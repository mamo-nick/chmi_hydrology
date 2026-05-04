# CHMI Hydrology

🇬🇧 English | 🇨🇿 [Česky](README.cs.md)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![version](https://img.shields.io/badge/version-0.9.0-blue)

Home Assistant custom integration for monitoring river water levels, flow rates and flood activity using open data from the **Czech Hydrometeorological Institute (CHMI)** — [opendata.chmi.cz](https://opendata.chmi.cz).

> **Regional scope:** Data covers the **Czech Republic**. May also be of interest to users in neighbouring countries (Slovakia, Germany, Austria, Poland) for cross-border river monitoring.

The integration UI is available in multiple languages. Translations for English, Czech and Slovak are included.

---

## Features

- Search stations by river or town name
- Physical sensors: water level, flow rate, water temperature, forecasts
- Logical sensors: flood status (numeric + text), tendency
- Automatic map display — sensors with coordinates appear on the HA map automatically
- Auto-refresh every 10 minutes
- Multi-language UI

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
3. Enter a river or town name (e.g. `Elbe`, `Vltava`, `Orlice`)
4. Select one or more stations from the results
5. Confirm — sensors are created automatically

To add another station use **Add entry** on the integration card. To remove a station open the entry and delete it.

> **Note:** SPA flood thresholds and evaluation type (`SPA_TYP`) are saved from metadata when the station is added. The integration does not re-fetch metadata at runtime — if CHMI changes thresholds, re-add the station.

---

## Data Source

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

CHMI typically updates data every **10 minutes**. Field code reference: [Popis_kodu_now_a_recent.pdf](https://opendata.chmi.cz/hydrology/read_me/Popis_kodu_now_a_recent.pdf)

---

## Entities

Each configured station creates the following entities. Displayed names adapt to your HA language setting.

> **Finding entity IDs:** Entity IDs depend on the station name and your HA language. Find your actual entity IDs in **Developer Tools → States** by filtering for the river or station name.

### CHMI Code Mapping

| CHMI Code | Translation Key | Description |
|---|---|---|
| `H` | `water_level` | Water level |
| `H_F` | `water_level_fc` | Water level forecast |
| `Q` | `flow_rate` | Flow rate |
| `Q_F` | `flow_rate_fc` | Flow rate forecast |
| `T` / `TH` | `water_temp` | Water temperature |
| *(derived)* | `last_measurement` | Last measurement time |
| *(derived)* | `flood_status` | Flood status (numeric) |
| *(derived)* | `flood_status_desc` | Flood status (text) |
| *(derived)* | `trend` | Tendency |

### Physical Sensors

Created **only if the station provides that measurement**.

| Translation Key | Unit | Description |
|---|---|---|
| `water_level` | cm | Current water level |
| `water_level_fc` | cm | Water level forecast |
| `flow_rate` | m³/s | Current flow rate |
| `flow_rate_fc` | m³/s | Flow rate forecast |
| `water_temp` | °C | Water temperature |

The `water_level` and `flow_rate` sensors include `latitude` and `longitude` attributes — see [Map](#map) section below.

### Derived (Logical) Sensors

Always created regardless of what the station measures.

#### Last Measurement

Timestamp of the most recent reading (`timestamp` device class).

#### Flood Status (numeric)

Range: `-1` to `4`. Evaluated using `SPA_TYP` from station metadata:

| Value | Meaning | Condition |
|---|---|---|
| `-1` | Drought | below `DRYH` / `DRYQ` |
| `0` | Normal | below SPA1 threshold |
| `1` | SPA1 – Watch | ≥ `SPA1H` / `SPA1Q` |
| `2` | SPA2 – Advisory | ≥ `SPA2H` / `SPA2Q` |
| `3` | SPA3 – Warning | ≥ `SPA3H` / `SPA3Q` |
| `4` | SPA4 – Emergency | ≥ `SPA4H` / `SPA4Q` |

Threshold values are exposed as sensor attributes (`spa1_cm`, `drought_cm` or `spa1_m3s` etc.).

#### Flood Status (text)

Returns a translated state string corresponding to the numeric flood status.

#### Tendency

Compares average of last 3 readings (~30 min) with average of previous 3 readings (30–60 min ago).

| Value | Threshold |
|---|---|
| `falling_fast` | diff < −10 |
| `falling` | −10 ≤ diff < −3 |
| `falling_slow` | −3 ≤ diff < −1 |
| `steady` | −1 ≤ diff < +1 |
| `rising_slow` | +1 ≤ diff < +3 |
| `rising` | +3 ≤ diff < +10 |
| `rising_fast` | diff ≥ +10 |

Units: cm (H-type stations) or m³/s (Q-type). Returns `None` if less than ~60 min of history is available.

---

## Map

The `water_level` and `flow_rate` sensors include `latitude` and `longitude` attributes (WGS84). This means they **automatically appear on the HA map** without any additional configuration.

When multiple sensors are at the same location, click on the station marker first to see individual sensor values.

Optionally you can also use a dedicated map card:

```yaml
type: map
entities:
  - entity: sensor.YOUR_WATER_LEVEL_ENTITY
    name: "Station – Water Level"
  - entity: sensor.YOUR_FLOW_RATE_ENTITY
    name: "Station – Flow Rate"
hours_to_show: 0
```

---

## Dashboard Cards

> **Note:** The following graph examples use [ApexCharts Card](https://github.com/RomRider/apexcharts-card) which must be **installed separately via HACS** before use.

### 1. Water Level – History + Forecast

The measured curve uses **HA recorder history**. The forecast comes from the `forecast` attribute of the `water_level_fc` sensor.

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Station – Water Level
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
  - entity: sensor.YOUR_WATER_LEVEL_ENTITY
    name: Water Level
    stroke_width: 2
    color: "#0077b6"
  - entity: sensor.YOUR_WATER_LEVEL_FC_ENTITY
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

> Replace `165`, `200`, `220` with your station's actual SPA thresholds from the `flood_status` sensor attributes. Replace `YOUR_*_ENTITY` placeholders with actual entity IDs from Developer Tools.

---

### 2. Flow Rate – History + Forecast

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Station – Flow Rate
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
  - entity: sensor.YOUR_FLOW_RATE_ENTITY
    name: Flow Rate
    stroke_width: 2
    color: "#0077b6"
    unit: m³/s
  - entity: sensor.YOUR_FLOW_RATE_FC_ENTITY
    name: Forecast
    stroke_width: 2
    color: "#90e0ef"
    unit: m³/s
    data_generator: |
      return entity.attributes.forecast.map(h => [new Date(h.dt).getTime(), h.value]);
```

---

### 3. Flood Status Gauge

```yaml
type: gauge
entity: sensor.YOUR_FLOOD_STATUS_ENTITY
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

### 4. Station Overview

```yaml
type: entities
title: Station Name
entities:
  - entity: sensor.YOUR_WATER_LEVEL_ENTITY
  - entity: sensor.YOUR_FLOW_RATE_ENTITY
  - entity: sensor.YOUR_WATER_TEMP_ENTITY
  - entity: sensor.YOUR_TREND_ENTITY
  - entity: sensor.YOUR_FLOOD_STATUS_DESC_ENTITY
  - entity: sensor.YOUR_LAST_MEASUREMENT_ENTITY
```

---

### 5. Multi-Station Comparison

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: River Monitoring
graph_span: 24h
series:
  - entity: sensor.YOUR_STATION1_WATER_LEVEL
    name: Station 1
  - entity: sensor.YOUR_STATION2_WATER_LEVEL
    name: Station 2
```

---

## Automation Example

```yaml
automation:
  - alias: "Flood Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.YOUR_FLOOD_STATUS_ENTITY
        above: 1
    action:
      - service: notify.mobile_app
        data:
          message: >
            Flood alert! Station reached
            {{ states('sensor.YOUR_FLOOD_STATUS_DESC_ENTITY') }}.
            Water level: {{ states('sensor.YOUR_WATER_LEVEL_ENTITY') }} cm
```

---

## License

MIT License. Data provided by [CHMI](https://www.chmi.cz) under open data license.

Technical architecture: [Architecture.md](Architecture.md).
