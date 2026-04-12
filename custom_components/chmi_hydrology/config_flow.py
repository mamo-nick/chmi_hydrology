"""Config flow for CHMI Hydrology integration."""
from __future__ import annotations

import logging
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


def _stations_to_options(stations: list[dict]) -> list[SelectOptionDict]:
    """Convert station list to SelectOptionDict for SelectSelector."""
    return [
        SelectOptionDict(
            value=s["objID"],
            label=f"{s['STREAM_NAME']} {s['STATION_NAME']} ({s['DBC']})",
        )
        for s in stations
    ]


def _multi_select_schema(stations: list[dict]) -> vol.Schema:
    """Build schema with multi-select selector."""
    return vol.Schema({
        vol.Required("stations"): SelectSelector(
            SelectSelectorConfig(
                options=_stations_to_options(stations),
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
        self._selected_stations: list[dict] = []
        self._search_results: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1 – search for station."""
        errors: dict[str, str] = {}

        if not self._all_stations:
            self._all_stations = await fetch_all_stations(self.hass)
            if not self._all_stations:
                return self.async_abort(reason="cannot_fetch_stations")

        if user_input is not None:
            query = user_input.get("search", "").strip().lower()
            if len(query) < 2:
                errors["search"] = "search_too_short"
            else:
                self._search_results = [
                    s for s in self._all_stations
                    if query in s.get("STATION_NAME", "").lower()
                    or query in s.get("STREAM_NAME", "").lower()
                ]
                if not self._search_results:
                    errors["search"] = "no_results"
                else:
                    return await self.async_step_select()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("search"): str}),
            errors=errors,
            description_placeholders={"count": str(len(self._all_stations))},
        )

    async def async_step_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2 – select stations from results."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_ids = user_input.get("stations", [])
            if not selected_ids:
                errors["stations"] = "no_station_selected"
            else:
                self._selected_stations = [
                    s for s in self._search_results
                    if s["objID"] in selected_ids
                ]
                return await self.async_step_confirm()

        return self.async_show_form(
            step_id="select",
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
