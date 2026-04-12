# CHMI Hydrology

🇨🇿 [Česky](README.md) | 🇬🇧 English

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![version](https://img.shields.io/badge/version-1.0.0-blue)

Home Assistant custom integration for monitoring river water levels, flow rates and flood status using open data from the **Czech Hydrometeorological Institute (CHMI)** — [opendata.chmi.cz](https://opendata.chmi.cz).

Supports Czech 🇨🇿, Slovak 🇸🇰 and English 🇬🇧 UI.

---

## Features

- 🔍 Search stations by river or town name
- 📊 Physical sensors: water level, flow rate, water temperature, forecasts
- 🌊 Logical sensors: flood status (numeric + text), trend
- 🗺️ Map card support – stations displayed on map with current values
- ⏱️ Auto-refresh every 10 minutes
- 🌍 Multi-language: CS / SK / EN

---

## Requirements

- Home Assistant 2023.6 or newer
- HACS installed
- Internet access from HA instance

---

## Installation

### Via HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add URL: `https://github.com/mamo-nick/chmi_hydrology`
3. Category: Integration
4. Install **CHMI Hydrology**
5. Restart Home Assistant

### Manual

1. Download the latest release ZIP
2. Extract and copy the `chmi_hydrology/` folder to `config/custom_components/`
3. Restart Home Assistant

---

## Configuration

1. Go to **Settings → Integrations → Add Integration**
2. Search for **CHMI Hydrology**
3. Enter a river name or town (e.g. `Labe`, `Mitrov`, `Orlice`)
4. Select one or more stations from the results
5. Confirm — sensors are created automatically

To add more stations, click **Add Entry** on the integration card. To remove a station, click the entry and delete it.

---

## Data Source

Data is fetched from the CHMI Open Data API:

```
https://opendata.chmi.cz/hydrology/now/
```

Station metadata (names, coordinates, flood thresholds):
```
https://opendata.chmi.cz/hydrology/now/metadata/meta1.json
```

Station measurements:
```
https://opendata.chmi.cz/hydrology/now/data/{station_id}.json
```

Data is updated by CHMI every **10 minutes**. Field code reference: [Popis_kodu_now_a_recent.pdf](https://opendata.chmi.cz/hydrology/read_me/Popis_kodu_now_a_recent.pdf)

**Note:** Flood thresholds and `SPA_TYP` are saved from metadata when you add the station. The integration does not re-fetch full metadata while running — if CHMI changes thresholds, re-add the station or reconfigure the entry.

---

## Entities

Each configured station creates the following entities. All entity IDs use the station's CHMI ID (e.g. `0-203-1-039000`) and are language-independent. The displayed name adapts to your HA language setting.

### CHMI Code to Entity ID Mapping

The CHMI API uses short codes (`tsConID`) to identify measurement types. This integration maps them to readable entity IDs based on `translation_key`. The table below shows the full mapping:

| CHMI Code | Translation Key | Entity ID suffix | Description |
|---|---|---|---|
| `H` | `water_level` | `_water_level` | Water level |
| `H_F` | `water_level_fc` | `_water_level_fc` | Water level forecast |
| `Q` | `flow_rate` | `_flow_rate` | Flow rate |
| `Q_F` | `flow_rate_fc` | `_flow_rate_fc` | Flow rate forecast |
| `T` / `TH` | `water_temp` | `_water_temp` | Water temperature |
| *(derived)* | `last_measurement` | `_last_measurement` | Last measurement time |
| *(derived)* | `flood_status` | `_flood_status` | Flood status (numeric) |
| *(derived)* | `flood_status_desc` | `_flood_status_desc` | Flood status (text) |
| *(derived)* | `trend` | `_trend` | Water level / flow trend |

**Full entity ID format:** `sensor.{station_id_underscored}_{translation_key}`

Example for station `0-203-1-039000`:
```
sensor.0_203_1_039000_water_level
sensor.0_203_1_039000_flow_rate
sensor.0_203_1_039000_water_temp
sensor.0_203_1_039000_water_level_fc
sensor.0_203_1_039000_flow_rate_fc
sensor.0_203_1_039000_last_measurement
sensor.0_203_1_039000_flood_status
sensor.0_203_1_039000_flood_status_desc
sensor.0_203_1_039000_trend
```

**unique_id format:** `chmi_hydrology_{station_id}_{tsConID}` for each CHMI time series (`H`, `Q`, `T`, `TH`, …). Derived sensors use `chmi_hydrology_{station_id}_{suffix}` with suffix `last_measurement`, `flood_status`, `flood_status_desc`, or `trend`.

Examples: `chmi_hydrology_0-203-1-039000_H` (water level); `chmi_hydrology_0-203-1-039000_T` vs `…_TH` when both temperature series exist. Suggested entity IDs for `T` / `TH` are `{station_id}_water_temp_t` and `{station_id}_water_temp_th`.

> **Note on entity IDs:** The entity IDs listed above are **suggested** values only. You can rename them freely in the HA UI (**Settings → Integrations → device → entity → pencil icon**) and the change will survive restarts. HA tracks entities internally via `unique_id`, which is fixed and never changes.

---

### Physical Sensors

These sensors are created **only if the station provides that measurement**. Not all stations measure all values.

| Entity ID | CHMI Code | Unit | Description |
|---|---|---|---|
| `sensor.0_203_1_XXXXXX_water_level` | `H` | cm | Current water level |
| `sensor.0_203_1_XXXXXX_water_level_fc` | `H_F` | cm | Water level forecast |
| `sensor.0_203_1_XXXXXX_flow_rate` | `Q` | m³/s | Current flow rate |
| `sensor.0_203_1_XXXXXX_flow_rate_fc` | `Q_F` | m³/s | Flow rate forecast |
| `sensor.0_203_1_XXXXXX_water_temp` | `T` / `TH` | °C | Water temperature |

Physical sensor values come directly from the CHMI time series data (`tsConID` field). The last value from the `tsData` array is used as the current reading. Each sensor also exposes `measured_at` (ISO timestamp) and `stream` (river name) as attributes.

The `water_level` and `flow_rate` sensors additionally expose `latitude` and `longitude` attributes, enabling map card display.

### Derived (Logical) Sensors

These sensors are always created regardless of what the station measures. Their values are **calculated** from the raw data and station metadata.

#### Last Measurement

| Entity ID | Translation Key | Description |
|---|---|---|
| `sensor.0_203_1_XXXXXX_last_measurement` | `last_measurement` | Timestamp of the most recent reading |

Returns a `datetime` object (HA `timestamp` device class). Taken from the last `dt` field in the `H` or `Q` time series.

#### Flood Status (numeric)

| Entity ID | Translation Key | Range | Description |
|---|---|---|---|
| `sensor.0_203_1_XXXXXX_flood_status` | `flood_status` | -1 to 4 | Current flood activity level |

**How it works:**

Each station defines its evaluation method via the `SPA_TYP` field in metadata:
- `SPA_TYP = H` → evaluated against **water level** (cm) thresholds
- `SPA_TYP = Q` → evaluated against **flow rate** (m³/s) thresholds

The current reading is compared against the station's thresholds in descending order:

| Value | Meaning | Condition |
|---|---|---|
| `-1` | Drought | reading < `DRYH` or `DRYQ` |
| `0` | Normal | below SPA1 threshold |
| `1` | SPA1 – Watch | reading ≥ `SPA1H` or `SPA1Q` |
| `2` | SPA2 – Advisory | reading ≥ `SPA2H` or `SPA2Q` |
| `3` | SPA3 – Warning | reading ≥ `SPA3H` or `SPA3Q` |
| `4` | SPA4 – Emergency | reading ≥ `SPA4H` or `SPA4Q` |

Returns `None` if thresholds are not defined for the station or measurement data is unavailable.

Threshold values are exposed as attributes (e.g. `spa1_cm`, `spa2_cm`, `drought_cm` or `spa1_m3s` etc.).

#### Flood Status Description (text)

| Entity ID | Translation Key | Description |
|---|---|---|
| `sensor.0_203_1_XXXXXX_flood_status_desc` | `flood_status_desc` | Translated flood status label |

Returns the translated state string corresponding to the numeric flood status. Uses HA state translations — the displayed value adapts to the UI language.

| Internal value | EN | CS | SK |
|---|---|---|---|
| `dry` | Drought | Sucho | Sucho |
| `normal` | Normal | Normální stav | Normálny stav |
| `spa1` | SPA1 – Watch | 1. SPA – Bdělost | 1. SPA – Bdelosť |
| `spa2` | SPA2 – Advisory | 2. SPA – Pohotovost | 2. SPA – Pohotovosť |
| `spa3` | SPA3 – Warning | 3. SPA – Ohrožení | 3. SPA – Ohrozenie |
| `spa4` | SPA4 – Emergency | 4. SPA – Katastrofa | 4. SPA – Katastrofa |

#### Trend

| Entity ID | Translation Key | Description |
|---|---|---|
| `sensor.0_203_1_XXXXXX_trend` | `trend` | Water level / flow rate trend |

**How it works:**

The trend is calculated by comparing two 30-minute averages:
- **Recent window:** average of the last 3 readings (last 30 minutes)
- **Previous window:** average of readings 30–60 minutes ago

```
diff = avg(last 30 min) - avg(previous 30 min)
```

The difference is classified into 7 levels:

| Internal value | EN | CS | SK | Diff threshold |
|---|---|---|---|---|
| `falling_fast` | Falling Fast | Rychle klesá | Rýchlo klesá | diff < −10 |
| `falling` | Falling | Klesá | Klesá | −10 ≤ diff < −3 |
| `falling_slow` | Falling Slow | Mírně klesá | Mierne klesá | −3 ≤ diff < −1 |
| `steady` | Steady | Setrvalý | Setrvalý | −1 ≤ diff < +1 |
| `rising_slow` | Rising Slow | Mírně stoupá | Mierne stúpa | +1 ≤ diff < +3 |
| `rising` | Rising | Stoupá | Stúpa | +3 ≤ diff < +10 |
| `rising_fast` | Rising Fast | Rychle stoupá | Rýchlo stúpa | diff ≥ +10 |

Thresholds are in **cm** for H-type stations and **m³/s** for Q-type stations. Returns `None` if less than 60 minutes of history is available. The `difference` attribute contains the raw numeric difference.

---

## Dashboard Cards

### 1. Water Level History + Forecast (ApexCharts)

Combines measured history with forecast in a single graph. Flood stage thresholds are shown as horizontal reference lines.

The **measured** series uses Home Assistant **history** (recorder) — the integration does not expose CHMI raw `tsData` as an entity attribute. The **forecast** series uses the `forecast` attribute on `water_level_fc` / `flow_rate_fc` sensors.

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Dědina Mitrov – Water Level
graph_span: 48h
span:
  start: hour
  offset: "-24h"
now:
  show: true
  label: Now
apex_config:
  stroke:
    dashArray:
      - 0
      - 6
series:
  - entity: sensor.0_203_1_039000_water_level
    name: Water Level
    stroke_width: 2
    color: "#0077b6"
  - entity: sensor.0_203_1_039000_water_level_fc
    name: Forecast
    stroke_width: 2
    color: "#90e0ef"
    data_generator: |
      return entity.attributes.forecast.map(h => [new Date(h.dt).getTime(), h.value]);
yaxis:
  - min: ~0
    apex_config:
      plotLines:
        - value: 165
          color: "#ffd60a"
          width: 1
          label:
            text: SPA1
        - value: 200
          color: "#ff9500"
          width: 1
          label:
            text: SPA2
        - value: 220
          color: "#ff3a30"
          width: 1
          label:
            text: SPA3
```

> **Note:** Replace threshold values (`165`, `200`, `220`) with your station's actual SPA values from the `flood_status` sensor attributes.

---

### 2. Flow Rate History + Forecast (ApexCharts)

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Dědina Mitrov – Flow Rate
graph_span: 48h
span:
  start: hour
  offset: "-24h"
now:
  show: true
  label: Now
apex_config:
  stroke:
    dashArray:
      - 0
      - 6
series:
  - entity: sensor.0_203_1_039000_flow_rate
    name: Flow Rate
    stroke_width: 2
    color: "#0077b6"
    unit: m³/s
  - entity: sensor.0_203_1_039000_flow_rate_fc
    name: Forecast
    stroke_width: 2
    color: "#90e0ef"
    unit: m³/s
    data_generator: |
      return entity.attributes.forecast.map(h => [new Date(h.dt).getTime(), h.value]);
```

---

### 3. Flood Status Gauge

Visual gauge showing current flood stage with color zones.

```yaml
type: gauge
entity: sensor.0_203_1_039000_flood_status
name: Flood Status
min: -1
max: 4
severity:
  green: -1
  yellow: 1
  red: 3
needle: true
```

---

### 4. Station Overview Card

Quick overview of all key values for one station.

```yaml
type: entities
title: Dědina Mitrov
entities:
  - entity: sensor.0_203_1_039000_water_level
    name: Water Level
  - entity: sensor.0_203_1_039000_flow_rate
    name: Flow Rate
  - entity: sensor.0_203_1_039000_water_temp
    name: Water Temp
  - entity: sensor.0_203_1_039000_trend
    name: Trend
  - entity: sensor.0_203_1_039000_flood_status_desc
    name: Flood Status
  - entity: sensor.0_203_1_039000_last_measurement
    name: Last Measurement
```

---

### 5. Multi-Station Comparison (ApexCharts)

Compare water levels of multiple stations in one graph (uses HA history for each entity).

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: River Monitoring
graph_span: 24h
series:
  - entity: sensor.0_203_1_039000_water_level
    name: Dědina Mitrov
  - entity: sensor.0_203_1_037000_water_level
    name: Orlice Týniště
```

The `water_level` and `flow_rate` sensors both expose `latitude` and `longitude` attributes, enabling native HA map card support. When both sensors of the same station are added to the map card, HA merges them into a single point. Clicking the point shows both values.

```yaml
type: map
entities:
  - entity: sensor.0_203_1_039000_water_level
    name: "Dědina Mitrov – Water Level"
  - entity: sensor.0_203_1_039000_flow_rate
    name: "Dědina Mitrov – Flow Rate"
hours_to_show: 0
```

For multiple stations:

```yaml
type: map
entities:
  - entity: sensor.0_203_1_039000_water_level
    name: "Dědina Mitrov – Water Level"
  - entity: sensor.0_203_1_039000_flow_rate
    name: "Dědina Mitrov – Flow Rate"
  - entity: sensor.0_203_1_037000_water_level
    name: "Orlice Týniště – Water Level"
  - entity: sensor.0_203_1_037000_flow_rate
    name: "Orlice Týniště – Flow Rate"
hours_to_show: 0
```

---

## Automation Example

Send a notification when flood status reaches SPA2 or higher:

```yaml
automation:
  - alias: "Flood Alert – Orlice"
    trigger:
      - platform: numeric_state
        entity_id: sensor.0_203_1_037000_flood_status
        above: 1
    action:
      - service: notify.mobile_app
        data:
          message: >
            Flood alert! Orlice Týniště has reached
            {{ states('sensor.0_203_1_037000_flood_status_desc') }}.
            Water level: {{ states('sensor.0_203_1_037000_water_level') }} cm
```

---

## License

MIT License. Data provided by [CHMI](https://www.chmi.cz) under open data license.

Technical architecture: [Architecture.md](Architecture.md).
