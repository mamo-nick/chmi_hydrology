"""Extended history bootstrap for CHMI Hydrology.

Downloads the last HISTORY_BOOTSTRAP_DAYS days from the CHMI ``recent/``
endpoint, decimates the 10-minute samples into hourly averages, and imports
them directly into the water level / flow rate / temperature sensor
entities' *own* Long-Term Statistics (LTS) - so a freshly added station
shows a full month of history immediately, merged seamlessly into the
entity's built-in history graph. No separate dashboard card or statistic
namespace is needed to see it.

Uses ``async_import_statistics`` with ``source="recorder"`` and
``statistic_id`` set to the sensor entity's *real* ``entity_id`` (looked up
from the entity registry by ``unique_id`` - never guessed or constructed
from the station name, since the user may have renamed the entity). This is
the mechanism Home Assistant reserves for statistics tied to an existing
entity. It differs from ``async_add_external_statistics``, which is for
statistics with no corresponding entity at all - that's not our case, we
always have a live sensor for every bootstrapped series.

Because the statistic_id is the entity's own, Home Assistant's recorder
keeps extending this same history automatically forever once the entity
starts reporting real state changes (which it does the moment it is set
up) - no periodic "keep it fresh" task is required on our side.

CHMI publishes timestamps in local Czech time (CET/CEST). All datetimes
must be converted to timezone-aware UTC before being handed to
``async_import_statistics`` - see the timezone handling notes below.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any

import aiohttp

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    get_last_statistics,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    API_RECENT_URL,
    DOMAIN,
    HISTORY_BOOTSTRAP_DAYS,
    HISTORY_FETCH_DELAY,
    TIMEZONE_NAME,
    TS_DEFINITIONS,
)

_LOGGER = logging.getLogger(__name__)

# tsConID values that get a physical sensor entity AND are bootstrapped into
# that entity's own history. Forecast series (H_F, Q_F) are deliberately
# excluded - a forecast has no meaningful "history" of its own.
BOOTSTRAP_TS_IDS = {"H", "Q", "T", "TH"}


async def _fetch_recent_day(
    hass: HomeAssistant, station_id: str, day: date
) -> dict[str, Any] | None:
    """Fetch a single day's data from the recent/ endpoint.

    Returns None if the day is unavailable (HTTP 403/404 - either the
    station didn't exist yet, or the day rolled over into historical/
    at the start of a new calendar year). This is an expected condition,
    not an error.
    """
    date_str = day.strftime("%Y%m%d")
    url = API_RECENT_URL.format(date=date_str, station_id=station_id)
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status in (403, 404):
                _LOGGER.debug(
                    "recent/ data not available for station %s on %s (HTTP %s)",
                    station_id,
                    date_str,
                    resp.status,
                )
                return None
            if resp.status != 200:
                _LOGGER.debug(
                    "Unexpected status fetching recent/ for %s on %s: HTTP %s",
                    station_id,
                    date_str,
                    resp.status,
                )
                return None
            return await resp.json(content_type=None)
    except asyncio.TimeoutError:
        _LOGGER.debug("Timeout fetching recent/ for %s on %s", station_id, date_str)
        return None
    except aiohttp.ClientError as err:
        _LOGGER.debug(
            "Network error fetching recent/ for %s on %s: %s", station_id, date_str, err
        )
        return None


def _local_to_utc(dt_str: str) -> datetime | None:
    """Convert a CHMI local-time (Europe/Prague) timestamp string to UTC.

    CHMI timestamps are naive local time. We must:
    1. Attach the Europe/Prague timezone (zoneinfo handles CET/CEST
       transitions automatically - never hardcode a fixed offset).
    2. Convert to UTC before handing off to async_import_statistics,
       which requires timezone-aware UTC datetimes.
    """
    if not dt_str:
        return None
    try:
        naive = datetime.fromisoformat(dt_str.replace("Z", ""))
    except ValueError:
        return None

    tz = dt_util.get_time_zone(TIMEZONE_NAME)
    if tz is None:
        _LOGGER.warning("Could not resolve timezone %s", TIMEZONE_NAME)
        return None

    if naive.tzinfo is None:
        local_dt = naive.replace(tzinfo=tz)
    else:
        local_dt = naive

    return dt_util.as_utc(local_dt)


def _extract_samples(day_json: dict, ts_id: str) -> list[tuple[datetime, float]]:
    """Extract (utc_datetime, value) samples for one time series from a day's data."""
    samples: list[tuple[datetime, float]] = []
    try:
        obj = day_json["objList"][0]
        ts_list = obj.get("tsList", [])
    except (KeyError, IndexError):
        return samples

    for ts in ts_list:
        if ts.get("tsConID") != ts_id:
            continue
        for point in ts.get("tsData", []):
            value = point.get("value")
            dt_str = point.get("dt")
            if value is None or not dt_str:
                continue
            try:
                fval = float(value)
            except (TypeError, ValueError):
                continue
            utc_dt = _local_to_utc(dt_str)
            if utc_dt is None:
                continue
            samples.append((utc_dt, fval))

    return samples


def _hourly_average(samples: list[tuple[datetime, float]]) -> list[StatisticData]:
    """Decimate 10-minute samples into hourly averages (mean)."""
    buckets: dict[datetime, list[float]] = {}
    for dt_utc, value in samples:
        bucket_start = dt_utc.replace(minute=0, second=0, microsecond=0)
        buckets.setdefault(bucket_start, []).append(value)

    stats: list[StatisticData] = []
    for bucket_start in sorted(buckets):
        values = buckets[bucket_start]
        stats.append(
            StatisticData(
                start=bucket_start,
                mean=sum(values) / len(values),
                min=min(values),
                max=max(values),
            )
        )
    return stats


async def async_bootstrap_history(
    hass: HomeAssistant,
    station_id: str,
    stream_name: str,
    station_name: str,
    available_ts: list[str],
) -> bool:
    """Bootstrap up to HISTORY_BOOTSTRAP_DAYS of history into each sensor's LTS.

    Runs once per entity - if statistics already exist for a given
    entity_id, that series is skipped (covers both "bootstrap already ran"
    and "this is a later restart, the entity already has real history").
    Missing days (HTTP 403/404, e.g. a brand-new station, or the January
    rollover into historical/) are silently skipped; the bootstrap uses
    whatever days are available rather than failing.

    This function never raises - it runs as a background task and any
    failure here must not affect the rest of the integration.

    Returns True if at least one day of data was imported for any series.
    """
    try:
        return await _async_bootstrap_history_inner(
            hass, station_id, stream_name, station_name, available_ts
        )
    except Exception:  # noqa: BLE001 - background task must never crash HA
        _LOGGER.exception(
            "Unexpected error during history bootstrap for station %s", station_id
        )
        return False


async def _async_bootstrap_history_inner(
    hass: HomeAssistant,
    station_id: str,
    stream_name: str,
    station_name: str,
    available_ts: list[str],
) -> bool:
    """Do the actual bootstrap work (see async_bootstrap_history)."""
    today = dt_util.now(dt_util.get_time_zone(TIMEZONE_NAME)).date()
    days = [today - timedelta(days=i) for i in range(1, HISTORY_BOOTSTRAP_DAYS + 1)]

    # Fetch each day once, reuse across all time series for this station
    day_data: dict[date, dict[str, Any] | None] = {}
    for day in days:
        day_data[day] = await _fetch_recent_day(hass, station_id, day)
        await asyncio.sleep(HISTORY_FETCH_DELAY)

    days_found = sum(1 for v in day_data.values() if v is not None)
    any_imported = False

    entity_reg = er.async_get(hass)

    for ts_id in available_ts:
        if ts_id not in BOOTSTRAP_TS_IDS:
            continue

        # The matching ChmiStreamSensor's unique_id (see sensor.py) - look
        # up its *current* entity_id via the registry rather than
        # constructing one, so this keeps working after the user renames
        # the entity.
        unique_id = f"{DOMAIN}_{station_id}_{ts_id}"
        entity_id = entity_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
        if entity_id is None:
            _LOGGER.debug(
                "No entity registered yet for station %s (%s), skipping "
                "bootstrap for this series",
                station_id,
                ts_id,
            )
            continue

        # Skip if this entity already has statistics - either we already
        # bootstrapped it, or (on a restart weeks/months after install) it
        # has accumulated real history of its own by now.
        existing = await get_instance(hass).async_add_executor_job(
            get_last_statistics, hass, 1, entity_id, True, {"mean"}
        )
        if existing:
            _LOGGER.debug(
                "Statistics for %s already exist, skipping bootstrap", entity_id
            )
            continue

        all_samples: list[tuple[datetime, float]] = []
        for day_json in day_data.values():
            if day_json is not None:
                all_samples.extend(_extract_samples(day_json, ts_id))

        if not all_samples:
            _LOGGER.info(
                "No recent/ history available for station %s (%s) - "
                "this is expected for newly added stations",
                station_id,
                ts_id,
            )
            continue

        stats = _hourly_average(all_samples)
        if not stats:
            continue

        unit = TS_DEFINITIONS[ts_id]["unit"]
        metadata = StatisticMetaData(
            mean_type=StatisticMeanType.ARITHMETIC,
            has_sum=False,
            name=f"{stream_name} {station_name} {ts_id}",
            source="recorder",
            statistic_id=entity_id,
            unit_class=None,
            unit_of_measurement=unit,
        )
        _LOGGER.debug(
            "Importing statistics: entity_id=%r source='recorder' unit=%r "
            "stats_count=%d first_start=%r",
            entity_id,
            unit,
            len(stats),
            stats[0]["start"] if stats else None,
        )
        async_import_statistics(hass, metadata, stats)
        any_imported = True
        _LOGGER.info(
            "Imported %d hourly statistics for %s (%s)",
            len(stats),
            entity_id,
            ts_id,
        )

    if days_found < HISTORY_BOOTSTRAP_DAYS and days_found > 0:
        _LOGGER.info(
            "Station %s: only %d/%d days of history were available "
            "(this is normal near the start of a calendar year, when "
            "CHMI rotates recent/ data into historical/)",
            station_id,
            days_found,
            HISTORY_BOOTSTRAP_DAYS,
        )

    return any_imported
