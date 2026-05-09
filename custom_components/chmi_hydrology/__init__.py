"""CHMI Hydrology – Custom Integration for Home Assistant."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_STATIONS, DOMAIN
from .coordinator import ChmiHydrologyCoordinator

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

    _LOGGER.warning("=== CHMI calling forward_entry_setups ===")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.warning("=== CHMI forward_entry_setups DONE ===")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
