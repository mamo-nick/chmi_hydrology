# CHMI Hydrology

🇨🇿 Česky | 🇬🇧 [English](README.md)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![version](https://img.shields.io/badge/version-0.9.0-blue)

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
3. Zadej název řeky nebo obce (např. `Labe`, `Vltava`, `Orlice`)
4. Vyber jednu nebo více stanic z výsledků
5. Potvrď — senzory se vytvoří automaticky

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

> **Poznámka:** Níže uvedené příklady grafů vyžadují [ApexCharts Card](https://github.com/RomRider/apexcharts-card), který je nutno **samostatně nainstalovat přes HACS**.

### 1. Vodní stav – historie + předpověď

Naměřená křivka využívá **historii HA (recorder)**. Předpověď se bere z atributu `forecast` senzoru `water_level_fc`.

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Stanice – Vodní stav
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
  - entity: sensor.TVOJE_ENTITA_VODNI_STAV
    name: Vodní stav
    stroke_width: 2
    color: "#0077b6"
  - entity: sensor.TVOJE_ENTITA_VODNI_STAV_FC
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

> Nahraď `165`, `200`, `220` skutečnými prahy SPA z atributů senzoru `flood_status`. Entity ID najdeš ve **Vývojářské nástroje → Stavy**.

---

### 2. Průtok – historie + předpověď

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Stanice – Průtok
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
  - entity: sensor.TVOJE_ENTITA_PRUTOK
    name: Průtok
    stroke_width: 2
    color: "#0077b6"
    unit: m³/s
  - entity: sensor.TVOJE_ENTITA_PRUTOK_FC
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
entity: sensor.TVOJE_ENTITA_POVODNOVYSTAV
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
title: Název stanice
entities:
  - entity: sensor.TVOJE_ENTITA_VODNI_STAV
  - entity: sensor.TVOJE_ENTITA_PRUTOK
  - entity: sensor.TVOJE_ENTITA_TEPLOTA
  - entity: sensor.TVOJE_ENTITA_TENDENCE
  - entity: sensor.TVOJE_ENTITA_POVODNOVYSTAV_POPIS
  - entity: sensor.TVOJE_ENTITA_CAS_MERENI
```

---

### 5. Porovnání více stanic

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Sledování řek
graph_span: 24h
series:
  - entity: sensor.TVOJE_ENTITA_STANICE1_VODNI_STAV
    name: Stanice 1
  - entity: sensor.TVOJE_ENTITA_STANICE2_VODNI_STAV
    name: Stanice 2
```

---

## Příklad automatizace

```yaml
automation:
  - alias: "Povodňový alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.TVOJE_ENTITA_POVODNOVYSTAV
        above: 1
    action:
      - service: notify.mobile_app
        data:
          message: >
            Povodňový alert! Stanice dosáhla stupně
            {{ states('sensor.TVOJE_ENTITA_POVODNOVYSTAV_POPIS') }}.
            Vodní stav: {{ states('sensor.TVOJE_ENTITA_VODNI_STAV') }} cm
```

---

## Licence

MIT License. Data poskytuje [ČHMÚ](https://www.chmi.cz) v rámci otevřených dat.

Technický popis architektury: [Architecture.md](Architecture.md).
