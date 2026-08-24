"""CHMI Hydrology – Custom Integration for Home Assistant."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_STATIONS, DOMAIN
from .coordinator import ChmiHydrologyCoordinator
from .statistics_import import async_bootstrap_history

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""
    stations = entry.data.get(CONF_STATIONS, [])
    coordinators: dict[str, ChmiHydrologyCoordinator] = {}

    for station in stations:
        station_id = station["objID"]
        coordinator = ChmiHydrologyCoordinator(
            hass=hass,
            station_id=station_id,
            station_name=station["STATION_NAME"],
            stream_name=station["STREAM_NAME"],
        )
        coordinator.set_meta(station)
        coordinators[station_id] = coordinator
        _LOGGER.debug("Initializing station: %s (%s)", station["STATION_NAME"], station_id)

    await asyncio.gather(
        *[c.async_config_entry_first_refresh() for c in coordinators.values()]
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinators

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Bootstrap 30 days of history in the background - never blocks setup
    # and never fails setup if CHMI's recent/ endpoint has no data for
    # this station (e.g. a brand-new station, or the January rollover).
    for station in stations:
        station_id = station["objID"]
        coordinator = coordinators[station_id]
        entry.async_create_background_task(
            hass,
            async_bootstrap_history(
                hass,
                station_id=station_id,
                stream_name=station["STREAM_NAME"],
                station_name=station["STATION_NAME"],
                available_ts=coordinator.available_ts,
            ),
            name=f"chmi_hydrology_history_bootstrap_{station_id}",
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
