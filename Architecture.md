# CHMI Hydrology — Architecture

Technical design for contributors and advanced users. End-user setup is covered in the main [README](README.md).

## Overview

CHMI Hydrology is a Home Assistant custom integration that periodically fetches hydrological data from the [Czech Hydrometeorological Institute (CHMI) Open Data API](https://opendata.chmi.cz) and exposes it as sensor entities. Each configured station becomes one HA **device** with physical and derived sensors.

Design goals:

- **Separation of concerns**: config flow selects stations; `DataUpdateCoordinator` fetches and parses JSON; sensors read coordinator state and add presentation logic (e.g. trend).
- **Resilience**: HTTP errors, timeouts, invalid JSON, and unexpected payload shape surface as `UpdateFailed` for station data so HA can retry and surface diagnostics.

---

## Conceptual layers

```text
ČHMÚ API                    Home Assistant
─────────                   ─────────────────────────────────────────────
meta1.json  ──────────────► Config flow: search → multi-select → save
                            (metadata stored in ConfigEntry.data)

{station}.json ◄──────────  ChmiHydrologyCoordinator (polling, parse)
       ▲                    Sensor platform: entities from coordinator.data
       │                    Trend: derived in sensors from series history
       └────────────────    State machine / Entity Registry / UI
```

**Important:** Flood thresholds and `SPA_TYP` come from metadata captured **at config time**. The integration does **not** re-fetch `meta1.json` on every HA restart. If CHMI updates thresholds, the user must reconfigure or reload the integration after refreshing station data.

---

## Repository layout

```
custom_components/chmi_hydrology/
├── __init__.py          # Integration setup / teardown
├── config_flow.py       # GUI wizard
├── coordinator.py       # Fetch, parse, flood stage
├── sensor.py            # Sensor entities
├── const.py             # URLs, intervals, mappings
├── manifest.json
├── hacs.json            # HACS metadata (usually at repo root in published repos)
├── strings.json         # Default (EN) translation template
├── icons.json           # MDI icons per entity / state
├── icon.svg
└── translations/
    ├── en.json
    ├── cs.json
    └── sk.json
```

---

## Data flow

```
CHMI Open Data API
        │
        │  HTTP GET (station data every 10 min; meta on demand in config flow)
        ▼
ChmiHydrologyCoordinator
  ├── fetch_all_stations()  →  meta1.json (config flow only)
  └── _async_update_data()  →  {station_id}.json
        │
        │  parsed dict (available_ts, series, last_measurement, flood_stage, …)
        ▼
Sensor entities
  ├── ChmiStreamSensor       → physical measurements (H, Q, T, …)
  ├── ChmiLastMeasurementSensor
  ├── ChmiFloodStatusSensor / ChmiFloodStatusDescSensor
  └── ChmiTrendSensor
        │
        ▼
Home Assistant state machine
```

On platform load, the first coordinator refresh for all stations runs **in parallel** (`asyncio.gather`) so startup stays fast with multiple stations.

---

## API endpoints

| URL | Purpose | When |
|-----|---------|------|
| `https://opendata.chmi.cz/hydrology/now/metadata/meta1.json` | All stations, metadata, flood thresholds | Config flow (on demand) |
| `https://opendata.chmi.cz/hydrology/now/data/{station_id}.json` | Time series for one station | Every 600 s (10 min) |

Station IDs use CHMI/WIGOS-style strings, e.g. `0-203-1-XXXXXX`.

Requests use the Home Assistant shared HTTP session (`async_get_clientsession`), `aiohttp.ClientTimeout(total=30)`, and `content_type=None` when decoding JSON. Invalid JSON on station data raises `UpdateFailed`.

---

## Module reference

### `__init__.py`

1. Read `CONF_STATIONS` from the config entry.
2. Create one `ChmiHydrologyCoordinator` per station and call `set_meta()` with saved metadata (thresholds, coordinates, `SPA_TYP`, …).
3. Store coordinators in `hass.data[DOMAIN][entry_id]`.
4. Forward setup to the `sensor` platform.

On unload, remove the entry from `hass.data` and unload platforms.

### `config_flow.py`

Three steps: **Search** (filter `meta1.json` list) → **Select** (multi-select) → **Confirm**. If metadata cannot be fetched, the flow aborts with `cannot_fetch_stations`.

### `coordinator.py`

- `ChmiHydrologyCoordinator`: extends `DataUpdateCoordinator`; update interval `DEFAULT_SCAN_INTERVAL` (600 s).
- Fetches `{station_id}.json`, parses `objList[0].tsList`, fills `available_ts`, last value + full `history` per series, optional `forecast` for `H_F` / `Q_F`.
- Computes `last_measurement` from `H` or `Q`, and `flood_stage` via `_calculate_flood_stage` using stored metadata.
- `fetch_all_stations()` downloads and parses `meta1.json` (rows with column count mismatch are skipped with a warning).

### `sensor.py`

| Class | Role | Count per station |
|-------|------|-------------------|
| `ChmiStreamSensor` | Physical | One per available `tsConID` in `TS_DEFINITIONS` |
| `ChmiLastMeasurementSensor` | Derived | 1 |
| `ChmiFloodStatusSensor` | Derived | 1 |
| `ChmiFloodStatusDescSensor` | Derived | 1 |
| `ChmiTrendSensor` | Derived | 1 |

All extend `ChmiBaseSensor` (`CoordinatorEntity` + `SensorEntity`). `_attr_has_entity_name = True`; `unique_id` is stable; `entity_id` can be changed in the UI.

### `const.py`

API base URLs, `DEFAULT_SCAN_INTERVAL`, `TS_DEFINITIONS`, `FLOOD_THRESHOLDS`, `FLOOD_STATUS`.

### `icons.json`

MDI icons per sensor type; optional per-state icons for `flood_status_desc` and `trend`. No icon logic in Python.

### `translations/`

Config flow strings and `entity.sensor.*` names; state translations for flood description and trend keys.

---

## Entity identity

| | Format | Example |
|---|--------|---------|
| `unique_id` (stream) | `{domain}_{station_id}_{tsConID}` | `chmi_hydrology_0-203-1-039000_H` |
| `unique_id` (derived) | `{domain}_{station_id}_{suffix}` | `…_last_measurement`, `…_flood_status`, … |
| Suggested `entity_id` (stream) | `sensor.{station_slug}_{translation_key}` or `{station_slug}_water_temp_t` / `_th` for `T` / `TH` | `sensor.0_203_1_039000_water_level` |

HA tracks entities by `unique_id`; renames are safe across restarts.

---

## Sensor logic

### Flood stage (`SPA`)

```
SPA_TYP = H  →  compare current H (cm)  to DRYH, SPA1H–SPA4H
SPA_TYP = Q  →  compare current Q (m³/s) to DRYQ, SPA1Q–SPA4Q

Evaluation (highest stage first):
  current ≥ SPA4  →  4
  current ≥ SPA3  →  3
  current ≥ SPA2  →  2
  current ≥ SPA1  →  1
  current < DRY   →  -1   (drought)
  else            →  0   (normal)
```

Returns `None` if thresholds or current measurement are missing/invalid.

### Trend

```
recent   = average of last 3 samples   (~30 min if 10-min step)
previous = average of samples [-6:-3] (prior ~30 min window)
diff     = recent − previous

Threshold bands (example; see TREND_LEVELS in code):
  diff < -10       → falling_fast
  …                → … (falling, falling_slow, steady, rising_slow, rising, rising_fast)
```

Units: cm for H-type stations, m³/s for Q-type. Returns `None` if fewer than six history points are available (`<` ~60 min of data). Invalid sample values are skipped when building averages.

---

## Device grouping

Shared `DeviceInfo` per station:

- `identifiers`: `{(DOMAIN, station_id)}`
- `name`: `{stream_name} {station_name}`
- `manufacturer`: `CHMI`
- `model`: `Hydrological Station`

---

## Coordinates and maps

`water_level` (`H`) and `flow_rate` (`Q`) sensors expose `latitude` / `longitude` attributes (WGS84 from `GEOGR1` / `GEOGR2` in stored metadata) for map cards.

---

## Forecast series

For `H_F` and `Q_F`, the `forecast` attribute lists `{dt, value}` entries from the API series so custom cards (e.g. ApexCharts `data_generator`) can plot forecasts without extra storage.

---

## Presentation layer

The integration does not ship a custom Lovelace UI. Dashboards, history, and optional community cards (e.g. ApexCharts) consume standard entities and attributes.
