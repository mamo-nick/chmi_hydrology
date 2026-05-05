"""Config flow for CHMI Hydrology integration."""
from __future__ import annotations

import logging
import math
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SelectOptionDict,
)

from .const import CONF_STATIONS, DOMAIN
from .coordinator import fetch_all_stations

_LOGGER = logging.getLogger(__name__)

# Radius for nearby stations in km
NEARBY_RADIUS_KM = 10.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS points in km (Haversine formula)."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_nearby_stations(
    all_stations: list[dict], home_lat: float, home_lon: float
) -> list[dict]:
    """Return nearby stations within NEARBY_RADIUS_KM, or just the closest one."""
    stations_with_dist = []
    for s in all_stations:
        try:
            lat = float(s["GEOGR1"])
            lon = float(s["GEOGR2"])
        except (TypeError, ValueError, KeyError):
            continue
        dist = _haversine_km(home_lat, home_lon, lat, lon)
        stations_with_dist.append((dist, s))

    stations_with_dist.sort(key=lambda x: x[0])

    # All stations within radius
    within = [(d, s) for d, s in stations_with_dist if d <= NEARBY_RADIUS_KM]
    if within:
        return [s for _, s in within]

    # No stations within radius – return just the closest one
    if stations_with_dist:
        return [stations_with_dist[0][1]]

    return []


def _stations_to_options(
    stations: list[dict], distances: dict[str, float] | None = None
) -> list[SelectOptionDict]:
    """Convert station list to SelectOptionDict for SelectSelector."""
    options = []
    for s in stations:
        label = f"{s['STREAM_NAME']} {s['STATION_NAME']} ({s['DBC']})"
        if distances and s["objID"] in distances:
            label += f" – {distances[s['objID']]:.1f} km"
        options.append(SelectOptionDict(value=s["objID"], label=label))
    return options


def _multi_select_schema(
    stations: list[dict],
    default: list[str] | None = None,
    distances: dict[str, float] | None = None,
) -> vol.Schema:
    """Build schema with multi-select selector."""
    options = _stations_to_options(stations, distances)
    field = (
        vol.Required("stations", default=default)
        if default is not None
        else vol.Required("stations")
    )
    return vol.Schema({
        field: SelectSelector(
            SelectSelectorConfig(
                options=options,
                multiple=True,
                mode=SelectSelectorMode.LIST,
            )
        )
    })


def _station_to_config(s: dict) -> dict:
    """Convert station record to config dict."""
    return {
        "objID":        s["objID"],
        "DBC":          s["DBC"],
        "STATION_NAME": s["STATION_NAME"],
        "STREAM_NAME":  s["STREAM_NAME"],
        "SPA_TYP":      s.get("SPA_TYP"),
        "GEOGR1":       s.get("GEOGR1"),
        "GEOGR2":       s.get("GEOGR2"),
        "DRYH":         s.get("DRYH"),
        "SPA1H":        s.get("SPA1H"),
        "SPA2H":        s.get("SPA2H"),
        "SPA3H":        s.get("SPA3H"),
        "SPA4H":        s.get("SPA4H"),
        "DRYQ":         s.get("DRYQ"),
        "SPA1Q":        s.get("SPA1Q"),
        "SPA2Q":        s.get("SPA2Q"),
        "SPA3Q":        s.get("SPA3Q"),
        "SPA4Q":        s.get("SPA4Q"),
    }


class ChmiHydrologyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for CHMI Hydrology."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._all_stations: list[dict] = []
        self._nearby_stations: list[dict] = []
        self._nearby_distances: dict[str, float] = {}
        self._search_results: list[dict] = []
        self._selected_stations: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1 – show nearby stations + optional search."""
        errors: dict[str, str] = {}

        # Load all stations on first visit
        if not self._all_stations:
            self._all_stations = await fetch_all_stations(self.hass)
            if not self._all_stations:
                return self.async_abort(reason="cannot_fetch_stations")

            # Find nearby stations using HA home coordinates
            home_lat = self.hass.config.latitude
            home_lon = self.hass.config.longitude
            if home_lat and home_lon:
                nearby = _get_nearby_stations(self._all_stations, home_lat, home_lon)
                self._nearby_stations = nearby
                # Calculate distances for display
                for s in nearby:
                    try:
                        dist = _haversine_km(
                            home_lat, home_lon,
                            float(s["GEOGR1"]), float(s["GEOGR2"])
                        )
                        self._nearby_distances[s["objID"]] = dist
                    except (TypeError, ValueError):
                        pass

        if user_input is not None:
            query = user_input.get("search", "").strip().lower()
            nearby_selected = user_input.get("nearby_stations", [])

            # Process search if query provided
            if query:
                if len(query) < 2:
                    errors["search"] = "search_too_short"
                else:
                    nearby_ids = {s["objID"] for s in self._nearby_stations}
                    self._search_results = [
                        s for s in self._all_stations
                        if (
                            query in s.get("STATION_NAME", "").lower()
                            or query in s.get("STREAM_NAME", "").lower()
                        )
                        and s["objID"] not in nearby_ids  # exclude already shown nearby
                    ]
                    if not self._search_results and not nearby_selected:
                        errors["search"] = "no_results"
                    elif self._search_results:
                        # Store nearby selection and go to search results step
                        self._selected_stations = [
                            s for s in self._nearby_stations
                            if s["objID"] in nearby_selected
                        ]
                        return await self.async_step_search_select()

            if not errors:
                # Collect selected nearby stations
                selected_nearby = [
                    s for s in self._nearby_stations
                    if s["objID"] in nearby_selected
                ]
                if not selected_nearby and not query:
                    errors["nearby_stations"] = "no_station_selected"
                elif not errors:
                    self._selected_stations = selected_nearby
                    return await self.async_step_confirm()

        # Build schema
        schema_fields: dict = {}

        # Nearby stations section (if available)
        if self._nearby_stations:
            nearby_ids = [s["objID"] for s in self._nearby_stations]
            schema_fields[vol.Required("nearby_stations", default=nearby_ids)] = (
                SelectSelector(
                    SelectSelectorConfig(
                        options=_stations_to_options(
                            self._nearby_stations, self._nearby_distances
                        ),
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                )
            )

        # Search field
        schema_fields[vol.Optional("search")] = str

        # Determine step description placeholders
        placeholders: dict[str, str] = {
            "count": str(len(self._all_stations)),
            "radius": str(int(NEARBY_RADIUS_KM)),
        }
        if self._nearby_stations:
            placeholders["nearby_count"] = str(len(self._nearby_stations))

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_fields),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_search_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2 – select from search results (combined with already selected nearby)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_ids = user_input.get("stations", [])
            search_selected = [
                s for s in self._search_results
                if s["objID"] in selected_ids
            ]
            self._selected_stations = self._selected_stations + search_selected
            if not self._selected_stations:
                errors["stations"] = "no_station_selected"
            else:
                return await self.async_step_confirm()

        return self.async_show_form(
            step_id="search_select",
            data_schema=_multi_select_schema(self._search_results),
            errors=errors,
            description_placeholders={"count": str(len(self._search_results))},
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3 – confirm and save."""
        if user_input is not None:
            return self.async_create_entry(
                title=", ".join(
                    f"{s['STREAM_NAME']} {s['STATION_NAME']}"
                    for s in self._selected_stations
                ),
                data={
                    CONF_STATIONS: [
                        _station_to_config(s) for s in self._selected_stations
                    ]
                },
            )

        names = "\n".join(
            f"• {s['STREAM_NAME']} {s['STATION_NAME']} ({s['DBC']})"
            for s in self._selected_stations
        )
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"stations": names},
        )
