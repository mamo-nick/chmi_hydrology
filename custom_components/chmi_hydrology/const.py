"""Constants for the CHMI Hydrology integration."""

DOMAIN = "chmi_hydrology"
MANUFACTURER = "CHMI"
NAME = "CHMI Hydrology"

# API URLs
API_BASE = "https://opendata.chmi.cz/hydrology/now"
API_META_URL = f"{API_BASE}/metadata/meta1.json"
API_DATA_URL = f"{API_BASE}/data/{{station_id}}.json"

# Update interval (seconds)
DEFAULT_SCAN_INTERVAL = 600  # 10 minutes

# Config keys
CONF_STATIONS = "stations"

# Time series type definitions: tsConID → translation_key, unit, device_class
TS_DEFINITIONS = {
    "H": {
        "translation_key": "water_level",
        "unit": "cm",
        "device_class": None,
    },
    "H_F": {
        "translation_key": "water_level_fc",
        "unit": "cm",
        "device_class": None,
    },
    "Q": {
        "translation_key": "flow_rate",
        "unit": "m³/s",
        "device_class": None,
    },
    "Q_F": {
        "translation_key": "flow_rate_fc",
        "unit": "m³/s",
        "device_class": None,
    },
    "T": {
        "translation_key": "water_temp",
        "unit": "°C",
        "device_class": "temperature",
    },
    "TH": {
        "translation_key": "water_temp",
        "unit": "°C",
        "device_class": "temperature",
    },
}

# Flood threshold keys in metadata per evaluation type (H or Q)
FLOOD_THRESHOLDS = {
    "H": {
        "dry":  "DRYH",
        "spa1": "SPA1H",
        "spa2": "SPA2H",
        "spa3": "SPA3H",
        "spa4": "SPA4H",
        "ts_id": "H",
    },
    "Q": {
        "dry":  "DRYQ",
        "spa1": "SPA1Q",
        "spa2": "SPA2Q",
        "spa3": "SPA3Q",
        "spa4": "SPA4Q",
        "ts_id": "Q",
    },
}

# Flood status: numeric value → translation_key
FLOOD_STATUS = {
    -1: {"translation_key": "dry"},
     0: {"translation_key": "normal"},
     1: {"translation_key": "spa1"},
     2: {"translation_key": "spa2"},
     3: {"translation_key": "spa3"},
     4: {"translation_key": "spa4"},
}
