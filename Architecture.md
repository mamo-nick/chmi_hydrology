# CHMI Hydrology – Architecture

## Overview

CHMI Hydrology is a Home Assistant custom integration that periodically fetches hydrological data from the Czech Hydrometeorological Institute (CHMI) Open Data API and exposes it as HA sensor entities. Each configured station becomes a HA device with a set of physical and derived sensors.

---

## File Structure

```
custom_components/chmi_hydrology/
├── __init__.py          # Integration setup and teardown
├── config_flow.py       # GUI configuration wizard
├── coordinator.py       # Data fetching and caching
├── sensor.py            # Sensor entity definitions
├── const.py             # Constants and data mappings
├── manifest.json        # HA integration manifest
├── hacs.json            # HACS metadata (repository root)
├── strings.json         # Translation template (EN)
├── icons.json           # MDI icon definitions per entity
├── icon.svg             # Integration logo (for HACS)
└── translations/
    ├── en.json          # English translations
    ├── cs.json          # Czech translations
    └── sk.json          # Slovak translations
```

---

## Data Flow

```
CHMI Open Data API
        │
        │  HTTP GET (every 10 min)
        ▼
ChmiHydrologyCoordinator
  ├── fetches meta1.json     → station list (config flow)
  └── fetches {station}.json → measurement data
        │
        │  parsed dict
        ▼
Sensor entities
  ├── ChmiStreamSensor       → physical measurements
  ├── ChmiLastMeasurementSensor
  ├── ChmiFloodStatusSensor  → derived / logical
  ├── ChmiFloodStatusDescSensor
  └── ChmiTrendSensor
        │
        ▼
Home Assistant state machine
```

---

## API Endpoints

| URL | Purpose | Update |
|---|---|---|
| `opendata.chmi.cz/hydrology/now/metadata/meta1.json` | All stations with metadata and flood thresholds | On demand (config flow) |
| `opendata.chmi.cz/hydrology/now/data/{station_id}.json` | Measurement time series for one station | Every 10 minutes |

Station ID format: `0-203-1-XXXXXX` (WIGOS identifier)

---

## Module Descriptions

### `__init__.py`
Entry point for the integration. On setup (`async_setup_entry`):
1. Reads station list from config entry data
2. Creates one `ChmiHydrologyCoordinator` per station
3. Passes station metadata (flood thresholds, coordinates) to each coordinator via `set_meta()`
4. Forwards setup to the `sensor` platform

On unload (`async_unload_entry`): removes coordinators from `hass.data`.

### `config_flow.py`
Three-step GUI wizard:
1. **Search** – user types river or town name, integration filters the full station list from `meta1.json`
2. **Select** – user picks one or more stations from results using a multi-select list
3. **Confirm** – selected stations are saved to config entry data

Station data saved per entry: `objID`, `DBC`, `STATION_NAME`, `STREAM_NAME`, coordinates (`GEOGR1`/`GEOGR2`), flood thresholds (`DRYH`, `SPA1H`–`SPA4H`, `DRYQ`, `SPA1Q`–`SPA4Q`), and evaluation type (`SPA_TYP`).

### `coordinator.py`
`ChmiHydrologyCoordinator` extends `DataUpdateCoordinator`. Key responsibilities:

- Uses HA shared HTTP session (`async_get_clientsession`) — no per-request session creation
- Handles `asyncio.TimeoutError` and `aiohttp.ClientError` → raises `UpdateFailed`
- Parses `objList[0].tsList` from station JSON
- For forecast series (`H_F`, `Q_F`): stores full data array in `entry["forecast"]`
- Calculates `flood_stage` (-1 to 4) using `SPA_TYP` from metadata
- Calculates `last_measurement` timestamp from `H` or `Q` series

`fetch_all_stations()` is a standalone async function used by `config_flow.py` to download and parse `meta1.json`.

### `sensor.py`
Defines five sensor classes, all extending `ChmiBaseSensor(CoordinatorEntity, SensorEntity)`:

| Class | Type | Count per station |
|---|---|---|
| `ChmiStreamSensor` | Physical | 1 per available `tsConID` |
| `ChmiLastMeasurementSensor` | Derived | Always 1 |
| `ChmiFloodStatusSensor` | Derived | Always 1 |
| `ChmiFloodStatusDescSensor` | Derived | Always 1 |
| `ChmiTrendSensor` | Derived | Always 1 |

All sensors use `_attr_has_entity_name = True` — displayed name = device name + entity name. Entity IDs are suggested via `_attr_suggested_object_id` and can be renamed by the user in HA UI without breaking tracking (HA uses `unique_id` internally).

### `const.py`
Defines:
- API URLs and update interval
- `TS_DEFINITIONS` — maps CHMI `tsConID` codes (`H`, `Q`, `T`, etc.) to `translation_key`, unit, and device class
- `FLOOD_THRESHOLDS` — maps `SPA_TYP` (`H`/`Q`) to the correct metadata field names
- `FLOOD_STATUS` — maps numeric flood stage (-1 to 4) to translation key

### `icons.json`
Declares MDI icons for each sensor type. Supports per-state icons for `flood_status_desc` (dry/normal/spa1–spa4) and `trend` (7 directional arrows). Icons are resolved by HA automatically — no icon logic in Python code.

### `translations/`
Three languages: `en`, `cs`, `sk`. Each file contains:
- Config flow UI strings (step titles, field labels, error messages)
- Entity display names (`entity.sensor.{translation_key}.name`)
- State translations for `flood_status_desc` and `trend`

---

## Entity Identity

Each entity has two identifiers:

| Identifier | Format | Example | Purpose |
|---|---|---|---|
| `unique_id` | `chmi_hydrology_{station_id}_{translation_key}` | `chmi_hydrology_0-203-1-039000_water_level` | Internal HA tracking, never changes |
| `entity_id` | `sensor.{station_slug}_{translation_key}` | `sensor.dedina_mitrov_vodni_stav` | User-visible, can be renamed |

`entity_id` is suggested via `_attr_suggested_object_id`. User renames survive restarts because HA tracks entities by `unique_id`.

---

## Sensor Logic

### Flood Stage Calculation

```
SPA_TYP = H  →  compare current H (cm) against DRYH, SPA1H–SPA4H
SPA_TYP = Q  →  compare current Q (m³/s) against DRYQ, SPA1Q–SPA4Q

Evaluation (highest stage first):
  current ≥ SPA4  →  4 (Emergency)
  current ≥ SPA3  →  3 (Warning)
  current ≥ SPA2  →  2 (Advisory)
  current ≥ SPA1  →  1 (Watch)
  current < DRY   →  -1 (Drought)
  else            →  0 (Normal)
```

Returns `None` if thresholds are not defined or measurement data is unavailable.

### Trend Calculation

```
recent   = avg of last 3 readings    (last 30 minutes, 10-min interval)
previous = avg of readings [-6:-3]   (30–60 minutes ago)
diff     = recent - previous

diff < -10      →  falling_fast
-10 ≤ diff < -3 →  falling
-3  ≤ diff < -1 →  falling_slow
-1  ≤ diff < +1 →  steady
+1  ≤ diff < +3 →  rising_slow
+3  ≤ diff < +10 → rising
diff ≥ +10      →  rising_fast
```

Units: cm for H-type stations, m³/s for Q-type. Returns `None` if fewer than 6 readings available (< 60 min of history).

---

## Device Grouping

All sensors of one station share the same `DeviceInfo`:
- `identifiers`: `{(DOMAIN, station_id)}`
- `name`: `{stream_name} {station_name}` (e.g. `Dědina Mitrov`)
- `manufacturer`: `CHMI`
- `model`: `Hydrological Station`

HA groups all entities under one device automatically.

---

## Coordinates and Map Support

`water_level` and `flow_rate` sensors expose `latitude` and `longitude` as state attributes (WGS84 decimal degrees, sourced from `GEOGR1`/`GEOGR2` in station metadata). This enables native HA map card support without any additional configuration.

---

## Forecast Data

`water_level_fc` (`H_F`) and `flow_rate_fc` (`Q_F`) sensors store the full forecast array in the `forecast` state attribute:

```json
"forecast": [
  {"dt": "2026-04-06T10:00:00Z", "value": 122.0},
  {"dt": "2026-04-06T11:00:00Z", "value": 120.0},
  ...
]
```

This enables ApexCharts-card `data_generator` to render forecast graphs directly from entity attributes without storing historical data in the HA recorder.

---

## Extended History Bootstrap

**Module:** `statistics_import.py`

**Source:** CHMI StoryMap "Otevřená data ČHMÚ – hydrologie: průvodce otevřenými daty"
(<https://storymaps.arcgis.com/stories/9296c701a3494ed69d0150dd9eeb295f>)

CHMI's `now/` endpoint provides the current day's data (10-minute samples). After midnight,
that day's data moves to the `recent/data/{YYYYMMDD}_{station_id}.json` endpoint, where it
stays - validated - until it is replaced by `historical/` data after one calendar year.

On first setup, the integration downloads up to `HISTORY_BOOTSTRAP_DAYS` (30) days of `recent/`
data as a background task (`entry.async_create_background_task`, started after platform setup
so it never blocks startup). Each day's 10-minute samples are decimated into hourly averages
(mean/min/max) and written **directly into the matching sensor entity's own Long-Term
Statistics** via `async_import_statistics`, with `source="recorder"` and `statistic_id` set to
that entity's real `entity_id` - looked up from the entity registry by `unique_id`, never
guessed from the station name, so it keeps working if the user renames the entity. Only the
physical measurement series (`H`, `Q`, `T`, `TH`) are bootstrapped; forecast series (`H_F`,
`Q_F`) are skipped since a forecast has no history of its own.

Because the statistic is the entity's own, the history is visible immediately in the entity's
built-in history/statistics graph - no separate dashboard card or statistic namespace is
needed - and Home Assistant's recorder keeps extending it automatically forever once the
entity starts reporting real state changes. No periodic "keep it fresh" task is needed on our
side.

Bootstrap runs once per entity - if statistics already exist for that `entity_id` (checked via
`get_last_statistics`), that series is skipped. This covers both "bootstrap already ran" and,
on a much later restart, "this entity has accumulated real history of its own by now, don't
overwrite it."

> **Note:** an earlier iteration of this feature wrote to a separate external statistic
> (`chmi_hydrology:{station_slug}_{ts_id}_history`, via `async_add_external_statistics`).
> That approach worked technically but left the imported history invisible in the entity's own
> history dialog and produced a snapshot that never grew past the original 30-day window. The
> entity-linked approach above supersedes it.

**Timezone handling:** CHMI timestamps are naive local time (CET/CEST). Each timestamp is
assigned the `Europe/Prague` zone via `dt_util.get_time_zone()` (which resolves DST
transitions automatically - no fixed offset is ever hardcoded), then converted to UTC via
`dt_util.as_utc()` before being handed to the recorder, which requires timezone-aware UTC.

**Missing data:** Individual days that return HTTP 403/404 (e.g. a brand-new station, or the
January rollover into `historical/`) are skipped; the bootstrap uses whatever days are
available rather than failing. If fewer than 30 days were found, this is logged at INFO level,
not as a warning - it is an expected condition, not an error.
