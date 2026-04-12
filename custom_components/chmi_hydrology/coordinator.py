"""Data update coordinator for CHMI Hydrology integration."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_DATA_URL,
    API_META_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FLOOD_THRESHOLDS,
)

_LOGGER = logging.getLogger(__name__)


class ChmiHydrologyCoordinator(DataUpdateCoordinator):
    """Coordinator for a single hydrological station."""

    def __init__(
        self,
        hass: HomeAssistant,
        station_id: str,
        station_name: str,
        stream_name: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{station_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.station_id = station_id
        self.station_name = station_name
        self.stream_name = stream_name
        self.available_ts: list[str] = []
        self._meta: dict = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest data from the station."""
        url = API_DATA_URL.format(station_id=self.station_id)
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(
                        f"Error fetching station {self.station_id}: HTTP {resp.status}"
                    )
                try:
                    raw = await resp.json(content_type=None)
                except json.JSONDecodeError as err:
                    raise UpdateFailed(
                        f"Invalid JSON for station {self.station_id}"
                    ) from err
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout fetching station {self.station_id}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Network error: {err}") from err

        return self._parse_data(raw)

    def _parse_data(self, raw: dict) -> dict[str, Any]:
        """Parse station JSON data."""
        result: dict[str, Any] = {}

        try:
            obj = raw["objList"][0]
            ts_list = obj.get("tsList", [])
        except (KeyError, IndexError) as err:
            raise UpdateFailed(f"Unexpected data structure: {err}") from err

        self.available_ts = []

        for ts in ts_list:
            ts_id = ts.get("tsConID")
            ts_data = ts.get("tsData", [])

            if not ts_id or not ts_data:
                continue

            self.available_ts.append(ts_id)

            last = ts_data[-1]
            entry: dict[str, Any] = {
                "value": last.get("value"),
                "dt": last.get("dt"),
                "history": ts_data,
            }

            # For forecast series store full data array as forecast attribute
            if ts_id in ("H_F", "Q_F"):
                entry["forecast"] = [
                    {"dt": h["dt"], "value": h["value"]}
                    for h in ts_data
                    if h.get("value") is not None
                ]

            result[ts_id] = entry

        # Last measurement timestamp (from H or Q)
        for base_ts in ("H", "Q"):
            if base_ts in result and result[base_ts].get("dt"):
                result["last_measurement"] = result[base_ts]["dt"]
                break

        result["flood_stage"] = self._calculate_flood_stage(result)

        return result

    def _calculate_flood_stage(self, data: dict) -> int | None:
        """Calculate flood stage based on SPA_TYP from station metadata.

        Returns:
            -1 = drought (below DRYH/DRYQ threshold)
             0 = normal
             1 = SPA1 – Watch
             2 = SPA2 – Advisory
             3 = SPA3 – Warning
             4 = SPA4 – Emergency
            None = cannot determine (missing data or thresholds)
        """
        if not self._meta:
            return None

        # Determine evaluation type from station metadata (H or Q), fallback to H
        spa_typ = self._meta.get("SPA_TYP", "H")
        thresholds = FLOOD_THRESHOLDS.get(spa_typ, FLOOD_THRESHOLDS["H"])

        # Current measured value
        ts_id = thresholds["ts_id"]
        current = None
        if ts_id in data and data[ts_id].get("value") is not None:
            try:
                current = float(data[ts_id]["value"])
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid value for %s: %s", ts_id, data[ts_id]["value"])
                return None

        if current is None:
            return None

        # Threshold values from metadata
        dry  = self._meta.get(thresholds["dry"])
        spa1 = self._meta.get(thresholds["spa1"])
        spa2 = self._meta.get(thresholds["spa2"])
        spa3 = self._meta.get(thresholds["spa3"])
        spa4 = self._meta.get(thresholds["spa4"])

        # Evaluate from highest stage downward
        if spa4 is not None and current >= float(spa4):
            return 4
        if spa3 is not None and current >= float(spa3):
            return 3
        if spa2 is not None and current >= float(spa2):
            return 2
        if spa1 is not None and current >= float(spa1):
            return 1

        # Drought – below dry threshold
        if dry is not None and current < float(dry):
            return -1

        return 0

    def set_meta(self, meta: dict) -> None:
        """Set station metadata (flood thresholds etc.)."""
        self._meta = meta


async def fetch_all_stations(hass: HomeAssistant) -> list[dict]:
    """Fetch list of all stations from meta1.json."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            API_META_URL, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status != 200:
                _LOGGER.error("Failed to fetch station metadata: HTTP %s", resp.status)
                return []
            try:
                raw = await resp.json(content_type=None)
            except json.JSONDecodeError:
                _LOGGER.exception("Invalid JSON in station metadata response")
                return []
    except asyncio.TimeoutError:
        _LOGGER.exception("Timeout fetching station metadata")
        return []
    except aiohttp.ClientError as err:
        _LOGGER.exception("Network error fetching station metadata: %s", err)
        return []

    return _parse_stations(raw)


def _parse_stations(raw: dict) -> list[dict]:
    """Parse meta1.json into a list of station dicts."""
    stations = []
    try:
        _LOGGER.debug("meta1 top-level keys: %s", list(raw.keys()))
        level1 = raw["data"]
        _LOGGER.debug("meta1 data keys: %s", list(level1.keys()) if isinstance(level1, dict) else type(level1))
        level2 = level1["data"]
        _LOGGER.debug("meta1 data.data keys: %s", list(level2.keys()) if isinstance(level2, dict) else type(level2))

        inner = raw["data"]["data"]
        headers = [h.strip() for h in inner["header"].split(",")]
        ncols = len(headers)
        for row in inner["values"]:
            if len(row) != ncols:
                _LOGGER.warning(
                    "Skipping station row: expected %s columns, got %s",
                    ncols,
                    len(row),
                )
                continue
            station = dict(zip(headers, row))
            stations.append(station)
    except (KeyError, TypeError) as err:
        _LOGGER.error("Error parsing station metadata: %s", err)
        _LOGGER.error("Raw data structure: %s", str(raw)[:500])

    return stations
