# CHMI Hydrology

🇨🇿 Česky | 🇬🇧 [English](README.md)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![version](https://img.shields.io/badge/version-0.9.2-blue)

Vlastní integrace pro Home Assistant umožňující sledování stavů řek, průtoků a povodňové aktivity pomocí otevřených dat **Českého hydrometeorologického ústavu (ČHMÚ)** — [opendata.chmi.cz](https://opendata.chmi.cz).

> **Regionální charakter:** Data pokrývají **Českou republiku**. Mohou být zajímavá i pro uživatele ze sousedních států (Slovensko, Německo, Rakousko, Polsko) – zejména příhraniční oblasti a přeshraniční toky.

Rozhraní integrace je vícejazyčné. K dispozici jsou překlady pro češtinu, angličtinu a slovenštinu.

---

## Funkce

- Vyhledání stanice podle názvu řeky nebo obce
- Fyzické senzory: vodní stav, průtok, teplota vody, předpovědi
- Logické senzory: povodňový stav (číselný + textový), tendence
- Automatické zobrazení na mapě — senzory se souřadnicemi se zobrazí na mapě HA automaticky
- Automatická aktualizace každých 10 minut
- Vícejazyčné rozhraní

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
3. Pokud máš v HA nastavenou polohu domova, nejbližší stanice (do 10 km) se zobrazí automaticky předvybrané
4. Můžeš také vyhledat libovolnou stanici podle názvu řeky nebo obce
5. Vyber jednu nebo více stanic a potvrď — senzory se vytvoří automaticky

Pro přidání další stanice použij **Přidat záznam** na kartě integrace. Pro odebrání stanice otevři záznam a smaž ho.

> **Poznámka:** Prahové hodnoty SPA a typ vyhodnocení (`SPA_TYP`) se uloží při přidání stanice z metadat. Integrace je za běhu z API znovu nestahuje — po změně u ČHMÚ může být potřeba stanici znovu přidat.

---

## Zdroj dat

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

---

## Entity

Každá nakonfigurovaná stanice vytvoří níže uvedené entity. Zobrazované názvy se řídí jazykem rozhraní HA.

> **Jak najít entity ID:** Entity ID závisí na názvu stanice a jazyce HA. Své entity najdeš v **Vývojářské nástroje → Stavy** filtrací podle názvu řeky nebo stanice.

### Mapování kódů ČHMÚ

| Kód ČHMÚ | Translation Key | Popis |
|---|---|---|
| `H` | `water_level` | Vodní stav |
| `H_F` | `water_level_fc` | Předpověď vodního stavu |
| `Q` | `flow_rate` | Průtok |
| `Q_F` | `flow_rate_fc` | Předpověď průtoku |
| `T` / `TH` | `water_temp` | Teplota vody |
| *(odvozeno)* | `last_measurement` | Čas posledního měření |
| *(odvozeno)* | `flood_status` | Povodňový stav (číselný) |
| *(odvozeno)* | `flood_status_desc` | Povodňový stav (textový) |
| *(odvozeno)* | `trend` | Tendence |

### Fyzické senzory

Vzniknou **jen pokud stanice danou veličinu poskytuje**.

| Translation Key | Jednotka | Popis |
|---|---|---|
| `water_level` | cm | Aktuální vodní stav |
| `water_level_fc` | cm | Předpověď hladiny |
| `flow_rate` | m³/s | Aktuální průtok |
| `flow_rate_fc` | m³/s | Předpověď průtoku |
| `water_temp` | °C | Teplota vody |

Senzory `water_level` a `flow_rate` mají atributy `latitude` a `longitude` — viz sekce [Mapa](#mapa) níže.

### Odvozené (logické) senzory

Vytvoří se **vždy** bez ohledu na to, co stanice měří.

#### Čas posledního měření

Časová značka posledního měření (typ `timestamp` v HA).

#### Povodňový stav (číselný)

Rozsah: `-1` až `4`. Vyhodnocuje se podle `SPA_TYP` z metadat stanice:

| Hodnota | Význam | Podmínka |
|---|---|---|
| `-1` | Sucho | pod `DRYH` / `DRYQ` |
| `0` | Normální stav | pod prahem SPA1 |
| `1` | 1. SPA – bdělost | ≥ `SPA1H` / `SPA1Q` |
| `2` | 2. SPA – pohotovost | ≥ `SPA2H` / `SPA2Q` |
| `3` | 3. SPA – ohrožení | ≥ `SPA3H` / `SPA3Q` |
| `4` | 4. SPA – katastrofa | ≥ `SPA4H` / `SPA4Q` |

Prahové hodnoty jsou v atributech senzoru (`spa1_cm`, `drought_cm` nebo `spa1_m3s` atd.).

#### Povodňový stav (textový)

Vrací přeložený popis odpovídající číselnému povodňovému stavu.

#### Tendence

Porovnání průměru posledních 3 měření (~30 min) s průměrem předchozích 3 měření (30–60 min zpět).

| Hodnota | Práh rozdílu |
|---|---|
| `falling_fast` | rozdíl < −10 |
| `falling` | −10 ≤ rozdíl < −3 |
| `falling_slow` | −3 ≤ rozdíl < −1 |
| `steady` | −1 ≤ rozdíl < +1 |
| `rising_slow` | +1 ≤ rozdíl < +3 |
| `rising` | +3 ≤ rozdíl < +10 |
| `rising_fast` | rozdíl ≥ +10 |

Jednotky: cm (H-type) nebo m³/s (Q-type). Vrací `None` pokud není k dispozici alespoň ~60 minut dat.

---

## Mapa

Senzory `water_level` a `flow_rate` mají atributy `latitude` a `longitude` (WGS84). Díky tomu se **automaticky zobrazují na velké mapě HA** bez jakékoliv další konfigurace.

Při více senzorech na stejném místě je třeba nejprve kliknout na značku stanice — zobrazí se hodnoty jednotlivých senzorů.

Volitelně lze použít také samostatnou mapovou kartu:

```yaml
type: map
entities:
  - entity: sensor.TVOJE_ENTITA_VODNI_STAV
    name: "Stanice – Vodní stav"
  - entity: sensor.TVOJE_ENTITA_PRUTOK
    name: "Stanice – Průtok"
hours_to_show: 0
```

---

## Karty dashboardu

> **Poznámka:** Příklady grafů vyžadují [ApexCharts Card](https://github.com/RomRider/apexcharts-card) a karty stavu/tendence vyžadují [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom). Obojí je nutno **samostatně nainstalovat přes HACS**.

> **Entity ID:** Nahraď entity ID v příkladech svými skutečnými entity ID. Najdeš je ve **Vývojářské nástroje → Stavy** filtrací podle názvu řeky nebo stanice.

### 1. Vodní stav + průtok

Kombinovaný graf se dvěma osami — vodní stav (levá osa, cm) a průtok (pravá osa, m³/s) s anotacemi SPA prahů.

![Graf vodního stavu a průtoku](docs/images/dashboard_water_level_flow.png)

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Název stanice
  show_states: true
  colorize_states: true
graph_span: 24h
apex_config:
  annotations:
    yaxis:
      - "y": 46
        borderColor: "#ff0000"
        strokeWidth: 1
        label:
          text: ↓ Sucho / Normální stav
          position: right
          style:
            colors: "#fff"
            background: "#a67b5b"
      - "y": 320
        borderColor: "#4caf50"
        strokeWidth: 1
        label:
          text: ↑ 1. SPA
          position: right
          style:
            colors: "#fff"
            background: "#4caf50"
      - "y": 350
        borderColor: "#ffd600"
        strokeWidth: 1
        label:
          text: ↑ 2. SPA
          position: right
          style:
            colors: "#000"
            background: "#ffd600"
      - "y": 370
        borderColor: "#f44336"
        strokeWidth: 1
        label:
          text: ↑ 3. SPA
          position: right
          style:
            colors: "#fff"
            background: "#f44336"
      - "y": 457
        borderColor: "#b71c1c"
        strokeWidth: 1
        label:
          text: ↑ 4. SPA
          position: right
          style:
            colors: "#fff"
            background: "#b71c1c"
  yaxis:
    - id: stav
      min: 0
    - id: prutok
      opposite: true
      min: 0
series:
  - entity: sensor.TVOJE_ENTITA_VODNI_STAV
    name: Stav
    unit: cm
    stroke_width: 2
    type: area
    opacity: 0.2
    color: "#3498db"
    yaxis_id: stav
  - entity: sensor.TVOJE_ENTITA_PRUTOK
    name: Průtok
    unit: m³/s
    type: line
    stroke_width: 2
    color: "#2ecc71"
    yaxis_id: prutok
```

> Nahraď hodnoty SPA prahů (`46`, `320`, `350`, `370`, `457`) hodnotami své stanice. Najdeš je v atributech senzoru `Povodňový stav` pod **Nastavení → Zařízení → entita → Podrobnosti**:

![Atributy povodňového stavu](docs/images/flood_status_attributes.png)

---

### 2. Povodňový stupeň + tendence

Dvě karty [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom) zobrazené vedle sebe.

![Povodňový stupeň a tendence](docs/images/dashboard_flood_status_trend.png)

**Karta povodňového stupně** — barva ikony odpovídá oficiálnímu barevnému označení ČHMÚ: světle modrá = normální stav, zelená = 1. SPA, žlutá = 2. SPA, červená = 3. SPA, tmavě červená = 4. SPA.

```yaml
type: custom:mushroom-template-card
primary: Povodňový stupeň
secondary: >-
  {{ state_translated('sensor.TVOJE_ENTITA_POVODNOVYSTAV_POPIS') }}
  ({{ states('sensor.TVOJE_ENTITA_VODNI_STAV') }} cm)
icon: mdi:waves
icon_color: >-
  {% set stav = states('sensor.TVOJE_ENTITA_POVODNOVYSTAV') | int %}
  {% if stav == -1 %}#5b9bd5
  {% elif stav == 0 %}#90caf9
  {% elif stav == 1 %}#4caf50
  {% elif stav == 2 %}#ffd600
  {% elif stav == 3 %}#f44336
  {% elif stav == 4 %}#b71c1c
  {% else %}#9e9e9e{% endif %}
fill_container: true
```

**Karta tendence** — ikona a barva se mění dynamicky podle aktuální tendence.

```yaml
type: custom:mushroom-template-card
primary: Tendence
secondary: >-
  {{ state_translated('sensor.TVOJE_ENTITA_TENDENCE') }}
  ({{ state_attr('sensor.TVOJE_ENTITA_TENDENCE', 'difference') }} cm)
icon: >-
  {% set stav = states('sensor.TVOJE_ENTITA_TENDENCE') %}
  {% if stav == 'falling_fast' %}mdi:arrow-down-bold
  {% elif stav == 'falling' %}mdi:arrow-down
  {% elif stav == 'falling_slow' %}mdi:arrow-bottom-right
  {% elif stav == 'steady' %}mdi:arrow-right
  {% elif stav == 'rising_slow' %}mdi:arrow-top-right
  {% elif stav == 'rising' %}mdi:arrow-up
  {% elif stav == 'rising_fast' %}mdi:arrow-up-bold
  {% else %}mdi:minus{% endif %}
icon_color: >-
  {% set stav = states('sensor.TVOJE_ENTITA_TENDENCE') %}
  {% if stav == 'falling_fast' %}#b71c1c
  {% elif stav == 'falling' %}#f44336
  {% elif stav == 'falling_slow' %}#90caf9
  {% elif stav == 'steady' %}#4caf50
  {% elif stav == 'rising_slow' %}#ffd600
  {% elif stav == 'rising' %}#ff9800
  {% elif stav == 'rising_fast' %}#b71c1c
  {% else %}#9e9e9e{% endif %}
fill_container: true
```

---

### 3. Přehled stanice

Vertical stack Mushroom karet s kompletním přehledem stanice.

![Přehled stanice](docs/images/dashboard_station_overview.png)

> **Poznámka:** Pokud stanice neposkytuje teplotu vody, odstraň kartu teploty z horizontal-stacku.

```yaml
title: Název stanice
type: vertical-stack
cards:
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Čas měření
        secondary: >-
          {{ states('sensor.TVOJE_ENTITA_CAS_MERENI') | as_timestamp
          | timestamp_custom('%d.%m.%Y %H:%M') }}
        icon: mdi:clock
        icon_color: "#9e9e9e"
        fill_container: true
      - type: custom:mushroom-template-card
        primary: Teplota vody
        secondary: "{{ states('sensor.TVOJE_ENTITA_TEPLOTA') }} °C"
        icon: mdi:thermometer
        icon_color: "#ff9800"
        fill_container: true
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Vodní stav
        secondary: "{{ states('sensor.TVOJE_ENTITA_VODNI_STAV') }} cm"
        icon: mdi:waves-arrow-up
        icon_color: "#0077b6"
        fill_container: true
      - type: custom:mushroom-template-card
        primary: Průtok
        secondary: "{{ states('sensor.TVOJE_ENTITA_PRUTOK') }} m³/s"
        icon: mdi:waves-arrow-right
        icon_color: "#2ecc71"
        fill_container: true
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-template-card
        primary: Povodňový stupeň
        secondary: >-
          {{ state_translated('sensor.TVOJE_ENTITA_POVODNOVYSTAV_POPIS') }}
          ({{ states('sensor.TVOJE_ENTITA_VODNI_STAV') }} cm)
        icon: mdi:waves
        icon_color: >-
          {% set stav = states('sensor.TVOJE_ENTITA_POVODNOVYSTAV') | int %}
          {% if stav == -1 %}#5b9bd5
          {% elif stav == 0 %}#90caf9
          {% elif stav == 1 %}#4caf50
          {% elif stav == 2 %}#ffd600
          {% elif stav == 3 %}#f44336
          {% elif stav == 4 %}#b71c1c
          {% else %}#9e9e9e{% endif %}
        fill_container: true
      - type: custom:mushroom-template-card
        primary: Tendence
        secondary: >-
          {{ state_translated('sensor.TVOJE_ENTITA_TENDENCE') }}
          ({{ state_attr('sensor.TVOJE_ENTITA_TENDENCE', 'difference') }} cm)
        icon: >-
          {% set stav = states('sensor.TVOJE_ENTITA_TENDENCE') %}
          {% if stav == 'falling_fast' %}mdi:arrow-down-bold
          {% elif stav == 'falling' %}mdi:arrow-down
          {% elif stav == 'falling_slow' %}mdi:arrow-bottom-right
          {% elif stav == 'steady' %}mdi:arrow-right
          {% elif stav == 'rising_slow' %}mdi:arrow-top-right
          {% elif stav == 'rising' %}mdi:arrow-up
          {% elif stav == 'rising_fast' %}mdi:arrow-up-bold
          {% else %}mdi:minus{% endif %}
        icon_color: >-
          {% set stav = states('sensor.TVOJE_ENTITA_TENDENCE') %}
          {% if stav == 'falling_fast' %}#b71c1c
          {% elif stav == 'falling' %}#f44336
          {% elif stav == 'falling_slow' %}#90caf9
          {% elif stav == 'steady' %}#4caf50
          {% elif stav == 'rising_slow' %}#ffd600
          {% elif stav == 'rising' %}#ff9800
          {% elif stav == 'rising_fast' %}#b71c1c
          {% else %}#9e9e9e{% endif %}
        fill_container: true
```

---

### 4. Mapa

Senzory `water_level` a `flow_rate` se automaticky zobrazují na mapě HA. Pro samostatnou mapovou kartu:

![Mapa stanice](docs/images/dashboard_map.png)

```yaml
type: map
entities:
  - entity: sensor.TVOJE_ENTITA_VODNI_STAV
    name: Stanice – Vodní stav
  - entity: sensor.TVOJE_ENTITA_PRUTOK
    name: Stanice – Průtok
hours_to_show: 0
theme_mode: auto
```

---

## Varování – automatizace

Automatizace posílá notifikaci při dosažení 1. SPA (bdělost). Trigger `numeric_state` se spustí **pouze jednou** při překročení hranice — neopakuje se dokud hodnota zůstane nad ní.

> Obdobně lze nastavit varování pro 2. SPA (`above: 1`), 3. SPA (`above: 2`) a 4. SPA (`above: 3`).

> Nahraď `notify.notify` svou konkrétní notifikační službou, např. `notify.mobile_app_tvuj_telefon`.

```yaml
alias: "Varování – Stanice 1. SPA"
triggers:
  - entity_id: sensor.TVOJE_ENTITA_POVODNOVYSTAV
    above: 0
    trigger: numeric_state
actions:
  - data:
      title: "⚠️ Varování – Stanice 1. SPA (bdělost)"
      message: >
        Dosažen 1. stupeň povodňové aktivity (bdělost)!
        Vodní stav: {{ states('sensor.TVOJE_ENTITA_VODNI_STAV') }} cm
        Průtok: {{ states('sensor.TVOJE_ENTITA_PRUTOK') }} m³/s
        Tendence: {{ state_translated('sensor.TVOJE_ENTITA_TENDENCE') }}
    action: notify.notify
```

---

## Licence

MIT License. Data poskytuje [ČHMÚ](https://www.chmi.cz) v rámci otevřených dat.

Technický popis architektury, datového toku a logiky senzorů: [Architecture.md](Architecture.md).
