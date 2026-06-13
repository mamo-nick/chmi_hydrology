# Changelog

All notable changes to CHMI Hydrology will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [0.9.5]

### Added
- Official CHMI brand icon and logo (with permission from CHMI)
- `brands/` updated with icon, icon_dark, logo, logo_dark (+ @2x variants)
- License & Attribution merged into the License section in README (CC BY 4.0, CHMI logo disclaimer)
- `decimalsInFloat: 0` on the water level Y-axis in the ApexCharts example for whole-cm display
- Moved data License & Attribution into the existing License section (previously under Data Source)

### Changed
- `custom_components/chmi_hydrology/icon.png` replaced with official CHMI mark
- Removed `icon.svg` (replaced by official PNG icon)
- Added `custom_components/chmi_hydrology/brand/` with local brand assets for HA 2026.3+ (icon.png, dark_icon.png, logo.png, dark_logo.png + @2x variants)
- Removed obsolete root `brands/` folder (not used by HA or HACS)
- Updated dashboard_water_level_flow.png screenshot

---

## [0.9.4] – 2026-06-07

### Fixed
- Sort manifest.json keys correctly (domain, name, then alphabetical) – required by Hassfest

### Added
- brand/ folder with icon.png and icon@2x.png inside integration directory – required by HACS validation
- GitHub Actions workflow for HACS and Hassfest validation

---

## [0.9.3] – 2026-06-05

### Fixed
- Multi-station setup: reverted to `source: import` for additional stations
- `async_step_import` restored (was incorrectly renamed to `async_step_user_additional`)

### Added
- Config flow screenshots in README (nearby stations, search results, confirmation)
- Integration device and entity overview screenshots in README
- Updated Configuration section in README.md and README.cs.md

---

## [0.9.2] – 2026-05-28

### Fixed
- Integration card now correctly appears in HA integrations dashboard
- Changed `integration_type` from `integration` to `hub` in `manifest.json`
- Removed `sensor` from `dependencies` in `manifest.json`

---

## [0.9.1] – 2026-05-28

### Fixed
- Integration card not showing in HA integrations dashboard
- Changed `source` from `import` to `SOURCE_USER` for multi-station config entries
- Moved `async_config_entry_first_refresh()` to `__init__.py` before `async_forward_entry_setups()`
- Use `Platform.SENSOR` enum instead of string `"sensor"` in `__init__.py`
- Removed duplicate `asyncio.gather` call from `sensor.py`
- Renamed `async_step_import` to `async_step_user_additional`

### Added
- Dashboard screenshots in `docs/images/`
- Dual-axis ApexCharts card example (water level + flow rate with SPA annotations)
- Mushroom Cards examples for flood status and tendency
- Station overview card (vertical-stack)
- Flood warning automation example
- `theme_mode: auto` for map card

### Changed
- README.md completely rewritten – EN as primary language
- README.cs.md updated with new dashboard card examples
- Removed gauge card example, replaced with Mushroom template card
- Dashboard cards now use `YOUR_*_ENTITY` placeholders for clarity

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
