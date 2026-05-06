# Changelog

All notable changes to CHMI Hydrology will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [0.9.0] – 2026-05-06

### Added
- Initial beta release
- Search stations by river or town name
- Auto-suggest nearby stations based on HA home location
- Physical sensors: water level, flow rate, water temperature, forecasts (H, Q, T/TH, H_F, Q_F)
- Derived sensors: flood status (numeric + text), tendency, last measurement
- Flood stage calculation based on `SPA_TYP` metadata (H or Q evaluation)
- Tendency calculation from 30-minute rolling averages (7 levels)
- `latitude` / `longitude` attributes on `water_level` and `flow_rate` sensors for HA map display
- Forecast data stored in `forecast` attribute for ApexCharts graphs
- Multi-language UI: English, Czech, Slovak
- One config entry per station (stations can be added/removed individually)
- Duplicate station prevention in config flow
- `icons.json` for MDI icon definitions per entity and state
- `hacs.json` with `country: CZ`
- GitHub issue templates (bug report, feature request)

### Technical
- Shared aiohttp session via `async_get_clientsession`
- `asyncio.TimeoutError` handling in coordinator
- `suggested_object_id` for predictable entity IDs
- `_attr_has_entity_name = True` for short entity display names

---

## [1.0.0] – planned

### Planned
- Stable release after beta testing
- Screenshots in README
- Submission to HACS default store
- Submission to home-assistant/brands
