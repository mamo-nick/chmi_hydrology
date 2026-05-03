# CHMI Hydrology

🇨🇿 Česky | 🇬🇧 [English](README.en.md)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![version](https://img.shields.io/badge/version-0.9.0-blue)

Vlastní integrace pro Home Assistant umožňující sledování stavů řek, průtoků a povodňové aktivity pomocí otevřených dat **Českého hydrometeorologického ústavu (ČHMÚ)** — [opendata.chmi.cz](https://opendata.chmi.cz).

Podporuje češtinu 🇨🇿, slovenštinu 🇸🇰 a angličtinu 🇬🇧 v rozhraní.

---

## Funkce

- Vyhledání stanice podle názvu řeky nebo obce
- Fyzické senzory: vodní stav, průtok, teplota vody, předpovědi
- Logické senzory: povodňový stav (číselný + textový), tendence
- Podpora mapové karty — stanice na mapě s aktuálními hodnotami
- Automatická aktualizace každých 10 minut
- Vícejazyčné rozhraní: CS / SK / EN

---

## Požadavky

- Home Assistant 2023.6 nebo novější
- Nainstalovaný HACS
- Přístup k internetu z instance HA

---

## Instalace

### Přes HACS (doporučeno)

1. Otevři HACS → Integrace → ⋮ → Vlastní repozitáře
2. Přidej URL: `https://github.com/mamo-nick/chmi_hydrology`
3. Kategorie: Integrace
4. Nainstaluj **CHMI Hydrology**
5. Restartuj Home Assistant

### Ručně

1. Stáhni aktuální ZIP ze stránky releases
2. Rozbal a zkopíruj složku `chmi_hydrology/` do `config/custom_components/`
3. Restartuj Home Assistant

---

## Konfigurace

1. Jdi do **Nastavení → Integrace → Přidat integraci**
2. Vyhledej **CHMI Hydrology**
3. Zadej název řeky nebo obce (např. `Labe`, `Mitrov`, `Orlice`)
4. Vyber jednu nebo více stanic z výsledků
5. Potvrď — senzory se vytvoří automaticky

Pro přidání další stanice použij **Přidat záznam** na kartě integrace. Pro odebrání stanice otevři záznam a smaž ho.

---

## Zdroj dat

Data se stahují z ČHMÚ Open Data API:

```
https://opendata.chmi.cz/hydrology/now/
```

Metadata stanic (názvy, souřadnice, povodňové prahy):

```
https://opendata.chmi.cz/hydrology/now/metadata/meta1.json
```

Měření stanice:

```
https://opendata.chmi.cz/hydrology/now/data/{station_id}.json
```

ČHMÚ data typicky aktualizuje každých **10 minut**. Popis kódů polí: [Popis_kodu_now_a_recent.pdf](https://opendata.chmi.cz/hydrology/read_me/Popis_kodu_now_a_recent.pdf)

**Poznámka:** Prahové hodnoty SPA a typ vyhodnocení (`SPA_TYP`) se uloží při přidání stanice z metadat. Integrace je za běhu z API znovu nestahuje — po změně u ČHMÚ může být potřeba záznam integrace znovu nastavit nebo znovu přidat stanici.

---

## Entity

Každá nakonfigurovaná stanice vytvoří níže uvedené entity. ID entit vycházejí z ID stanice ČHMÚ a jsou jazykově neutrální; zobrazované názvy se řídí jazykem rozhraní HA.

### Mapování kódů ČHMÚ na entity

API používá krátké kódy `tsConID`. Integrace je mapuje na čitelná ID podle `translation_key`:

| Kód ČHMÚ | Translation Key | Přípona entity ID | Popis |
|---|---|---|---|
| `H` | `water_level` | `_water_level` | Vodní stav |
| `H_F` | `water_level_fc` | `_water_level_fc` | Předpověď vodního stavu |
| `Q` | `flow_rate` | `_flow_rate` | Průtok |
| `Q_F` | `flow_rate_fc` | `_flow_rate_fc` | Předpověď průtoku |
| `T` / `TH` | `water_temp` | `_water_temp` | Teplota vody |
| *(odvozeno)* | `last_measurement` | `_last_measurement` | Čas posledního měření |
| *(odvozeno)* | `flood_status` | `_flood_status` | Povodňový stav (číselný) |
| *(odvozeno)* | `flood_status_desc` | `_flood_status_desc` | Povodňový stav (textový) |
| *(odvozeno)* | `trend` | `_trend` | Tendence hladiny / průtoku |

**Formát entity ID:** `sensor.{id_stanice_s_podtržítky}_{translation_key}`

Příklad pro stanici `0-203-1-039000`:

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

**Formát `unique_id`:** `chmi_hydrology_{id_stanice}_{translation_key}`

Příklad: `chmi_hydrology_0-203-1-039000_water_level`

> **Entity ID:** Uvedené hodnoty jsou jen **návrh** z HA. Uživatel je může přejmenovat (**Nastavení → Integrace → zařízení → entita → tužka**); při restartu zůstanou. HA entitu sleduje přes neměnné `unique_id`.

---

### Fyzické senzory

Vzniknou **jen pokud stanice danou veličinu poskytuje**. Ne všechny stanice mají všechny řady.

| Entity ID | Kód ČHMÚ | Jednotka | Popis |
|---|---|---|---|
| `sensor.0_203_1_XXXXXX_water_level` | `H` | cm | Aktuální vodní stav |
| `sensor.0_203_1_XXXXXX_water_level_fc` | `H_F` | cm | Předpověď hladiny |
| `sensor.0_203_1_XXXXXX_flow_rate` | `Q` | m³/s | Aktuální průtok |
| `sensor.0_203_1_XXXXXX_flow_rate_fc` | `Q_F` | m³/s | Předpověď průtoku |
| `sensor.0_203_1_XXXXXX_water_temp` | `T` / `TH` | °C | Teplota vody |

Hodnoty vycházejí z pole `tsData` v API; jako stav se použije poslední záznam. Atributy zahrnují `measured_at` (ISO čas) a `stream` (název toku).

Senzory `water_level` a `flow_rate` mají navíc `latitude` a `longitude` pro mapu.

---

### Odvozené (logické) senzory

Vytvoří se **vždy**. Hodnoty se **počítají** z měření a uložených metadat stanice.

#### Čas posledního měření

| Entity ID | Popis |
|---|---|
| `sensor.0_203_1_XXXXXX_last_measurement` | Časová značka posledního měření |

Typ `timestamp` v HA. Bere se z posledního `dt` řady `H` nebo `Q`.

#### Povodňový stav (číselný)

| Entity ID | Rozsah | Popis |
|---|---|---|
| `sensor.0_203_1_XXXXXX_flood_status` | -1 až 4 | Stupeň povodňové aktivity |

**Princip:** pole `SPA_TYP` v metadatech určuje, zda se porovnává **hladina (cm)** nebo **průtok (m³/s)**.

| Hodnota | Význam | Podmínka |
|---|---|---|
| `-1` | Sucho | hodnota < `DRYH` / `DRYQ` |
| `0` | Normální stav | pod prahem SPA1 |
| `1` | 1. SPA – bdělost | ≥ `SPA1H` / `SPA1Q` |
| `2` | 2. SPA – pohotovost | ≥ `SPA2H` / `SPA2Q` |
| `3` | 3. SPA – ohrožení | ≥ `SPA3H` / `SPA3Q` |
| `4` | 4. SPA – katastrofa | ≥ `SPA4H` / `SPA4Q` |

Je-li měření nebo prahy nedostupné, může být stav `unknown` / `None`. Prahové hodnoty jsou v atributech senzoru (`spa1_cm`, `drought_cm` nebo `spa1_m3s` atd.).

#### Povodňový stav (textový)

| Entity ID | Popis |
|---|---|
| `sensor.0_203_1_XXXXXX_flood_status_desc` | Přeložený popis stavu |

| Interní hodnota | CS | SK | EN |
|---|---|---|---|
| `dry` | Sucho | Sucho | Drought |
| `normal` | Normální stav | Normálny stav | Normal |
| `spa1` | 1. SPA – bdělost | 1. SPA – bdelosť | SPA1 – Watch |
| `spa2` | 2. SPA – pohotovost | 2. SPA – pohotovosť | SPA2 – Advisory |
| `spa3` | 3. SPA – ohrožení | 3. SPA – ohrozenie | SPA3 – Warning |
| `spa4` | 4. SPA – katastrofa | 4. SPA – katastrofa | SPA4 – Emergency |

#### Tendence

| Entity ID | Popis |
|---|---|
| `sensor.0_203_1_XXXXXX_trend` | Tendence hladiny nebo průtoku (dle `SPA_TYP`) |

Porovnání průměru **posledních tří** měření (~30 min) s průměrem **předchozích tří** (30–60 min zpět), při kroku dat 10 min.

| Interní hodnota | CS | Práh rozdílu |
|---|---|---|
| `falling_fast` | Rychle klesající | rozdíl < −10 |
| `falling` | Klesající | −10 ≤ rozdíl < −3 |
| `falling_slow` | Mírně klesající | −3 ≤ rozdíl < −1 |
| `steady` | Setrvalý stav | −1 ≤ rozdíl < +1 |
| `rising_slow` | Mírně stoupající | +1 ≤ rozdíl < +3 |
| `rising` | Stoupající | +3 ≤ rozdíl < +10 |
| `rising_fast` | Rychle stoupající | rozdíl ≥ +10 |

Jednotky: cm (H) nebo m³/s (Q). Atribut `difference` obsahuje číselný rozdíl. Bez alespoň ~60 minut historie v datech API je stav prázdný.

---

## Karty dashboardu

### 1. Vodní stav – historie + předpověď (ApexCharts)

**Naměřená** křivka využívá **historii Home Assistant** (recorder) — integrace **neexportuje** surové pole `tsData` jako atribut entity. **Předpověď** se bere z atributu `forecast` u senzorů `water_level_fc` / `flow_rate_fc`.

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Dědina Mitrov – Vodní stav
graph_span: 48h
span:
  start: hour
  offset: "-24h"
now:
  show: true
  label: Nyní
apex_config:
  stroke:
    dashArray:
      - 0
      - 6
series:
  - entity: sensor.0_203_1_039000_water_level
    name: Vodní stav
    stroke_width: 2
    color: "#0077b6"
  - entity: sensor.0_203_1_039000_water_level_fc
    name: Předpověď
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
            text: 1. SPA
        - value: 200
          color: "#ff9500"
          width: 1
          label:
            text: 2. SPA
        - value: 220
          color: "#ff3a30"
          width: 1
          label:
            text: 3. SPA
```

> Nahraď hodnoty `165`, `200`, `220` skutečnými prahy SPA z atributů senzoru `flood_status`.

---

### 2. Průtok – historie + předpověď (ApexCharts)

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Dědina Mitrov – Průtok
graph_span: 48h
span:
  start: hour
  offset: "-24h"
now:
  show: true
  label: Nyní
apex_config:
  stroke:
    dashArray:
      - 0
      - 6
series:
  - entity: sensor.0_203_1_039000_flow_rate
    name: Průtok
    stroke_width: 2
    color: "#0077b6"
    unit: m³/s
  - entity: sensor.0_203_1_039000_flow_rate_fc
    name: Předpověď
    stroke_width: 2
    color: "#90e0ef"
    unit: m³/s
    data_generator: |
      return entity.attributes.forecast.map(h => [new Date(h.dt).getTime(), h.value]);
```

---

### 3. Povodňový stav – ukazatel

```yaml
type: gauge
entity: sensor.0_203_1_039000_flood_status
name: Povodňový stav
min: -1
max: 4
severity:
  green: -1
  yellow: 1
  red: 3
needle: true
```

---

### 4. Přehled stanice

```yaml
type: entities
title: Dědina Mitrov
entities:
  - entity: sensor.0_203_1_039000_water_level
    name: Vodní stav
  - entity: sensor.0_203_1_039000_flow_rate
    name: Průtok
  - entity: sensor.0_203_1_039000_water_temp
    name: Teplota vody
  - entity: sensor.0_203_1_039000_trend
    name: Tendence
  - entity: sensor.0_203_1_039000_flood_status_desc
    name: Povodňový stav
  - entity: sensor.0_203_1_039000_last_measurement
    name: Poslední měření
```

---

### 5. Porovnání více stanic (ApexCharts)

Pro každou entitu se použije historie z HA (bez atributu `history`).

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Sledování řek
graph_span: 24h
series:
  - entity: sensor.0_203_1_039000_water_level
    name: Dědina Mitrov
  - entity: sensor.0_203_1_037000_water_level
    name: Orlice Týniště
```

Senzory `water_level` a `flow_rate` mají souřadnice pro nativní mapovou kartu. Při přidání obou ze stejné stanice HA je často sloučí do jednoho bodu.

```yaml
type: map
entities:
  - entity: sensor.0_203_1_039000_water_level
    name: "Dědina Mitrov – Vodní stav"
  - entity: sensor.0_203_1_039000_flow_rate
    name: "Dědina Mitrov – Průtok"
hours_to_show: 0
```

Více stanic:

```yaml
type: map
entities:
  - entity: sensor.0_203_1_039000_water_level
    name: "Dědina Mitrov – Vodní stav"
  - entity: sensor.0_203_1_039000_flow_rate
    name: "Dědina Mitrov – Průtok"
  - entity: sensor.0_203_1_037000_water_level
    name: "Orlice Týniště – Vodní stav"
  - entity: sensor.0_203_1_037000_flow_rate
    name: "Orlice Týniště – Průtok"
hours_to_show: 0
```

---

## Příklad automatizace

```yaml
automation:
  - alias: "Povodňový alert – Orlice"
    trigger:
      - platform: numeric_state
        entity_id: sensor.0_203_1_037000_flood_status
        above: 1
    action:
      - service: notify.mobile_app
        data:
          message: >
            Povodňový alert! Orlice Týniště dosáhla stupně
            {{ states('sensor.0_203_1_037000_flood_status_desc') }}.
            Vodní stav: {{ states('sensor.0_203_1_037000_water_level') }} cm
```

---

## Licence

MIT License. Data poskytuje [ČHMÚ](https://www.chmi.cz) v rámci otevřených dat.

Technický popis architektury: [Architecture.md](Architecture.md).
