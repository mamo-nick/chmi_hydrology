"""Sensor platform for CHMI Hydrology integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    FLOOD_STATUS,
    MANUFACTURER,
    TS_DEFINITIONS,
)
from .coordinator import ChmiHydrologyCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for all configured stations."""
    coordinators: dict[str, ChmiHydrologyCoordinator] = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    for station_id, coordinator in coordinators.items():
        # Physical measurement sensors (only for available time series)
        for ts_id in coordinator.available_ts:
            if ts_id in TS_DEFINITIONS:
                entities.append(ChmiStreamSensor(coordinator, ts_id))

        # Derived sensors
        entities.append(ChmiLastMeasurementSensor(coordinator))
        entities.append(ChmiFloodStatusSensor(coordinator))
        entities.append(ChmiFloodStatusDescSensor(coordinator))
        entities.append(ChmiTrendSensor(coordinator))

    async_add_entities(entities)


class ChmiBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for CHMI sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ChmiHydrologyCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._coordinator = coordinator

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this station."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._coordinator.station_id)},
            name=f"{self._coordinator.stream_name} {self._coordinator.station_name}",
            manufacturer=MANUFACTURER,
            model="Hydrological Station",
        )


class ChmiStreamSensor(ChmiBaseSensor):
    """Sensor for a single CHMI time series (water level, flow rate, temperature, forecast)."""

    def __init__(
        self,
        coordinator: ChmiHydrologyCoordinator,
        ts_id: str,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self._ts_id = ts_id
        self._def = TS_DEFINITIONS[ts_id]

        station_slug = coordinator.station_id.replace("-", "_")
        translation_key = self._def["translation_key"]
        # ts_id in unique_id: T and TH both use translation_key water_temp — must not collide
        self._attr_unique_id = f"{DOMAIN}_{coordinator.station_id}_{ts_id}"
        self._attr_translation_key = translation_key
        # suggested_object_id gives HA a hint for entity_id but allows user to change it
        if ts_id in ("T", "TH"):
            self._attr_suggested_object_id = f"{station_slug}_water_temp_{ts_id.lower()}"
        else:
            self._attr_suggested_object_id = f"{station_slug}_{translation_key}"
        self._attr_native_unit_of_measurement = self._def["unit"]
        self._attr_state_class = SensorStateClass.MEASUREMENT

        if self._def["device_class"] == "temperature":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE

    @property
    def native_value(self) -> float | None:
        """Return current sensor value."""
        if not self.coordinator.data:
            return None
        ts_data = self.coordinator.data.get(self._ts_id)
        if not ts_data:
            return None
        value = ts_data.get("value")
        if value is None:
            return None
        try:
            fval = float(value)
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid value for %s: %s", self._ts_id, value)
            return None
        # Round flow rate to 3 decimal places, temperature to 1, others as-is
        if "m³" in self._def["unit"]:
            return round(fval, 3)
        if getattr(self, "_attr_device_class", None) == SensorDeviceClass.TEMPERATURE:
            return round(fval, 1)
        return fval

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs: dict[str, Any] = {
            "stream": self._coordinator.stream_name,
            "station": self._coordinator.station_name,
            "station_id": self._coordinator.station_id,
        }
        if self.coordinator.data:
            ts_data = self.coordinator.data.get(self._ts_id)
            if ts_data and ts_data.get("dt"):
                attrs["measured_at"] = ts_data["dt"]

            # Forecast series – expose full forecast array as attribute
            if self._ts_id in ("H_F", "Q_F") and ts_data:
                attrs["forecast"] = ts_data.get("forecast", [])

        # Coordinates on water_level and flow_rate sensors for map display
        if self._ts_id in ("H", "Q"):
            meta = self._coordinator._meta
            if meta.get("GEOGR1") is not None:
                attrs["latitude"] = float(meta["GEOGR1"])
            if meta.get("GEOGR2") is not None:
                attrs["longitude"] = float(meta["GEOGR2"])

        return attrs


class ChmiLastMeasurementSensor(ChmiBaseSensor):
    """Sensor for last measurement timestamp."""

    def __init__(self, coordinator: ChmiHydrologyCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        station_slug = coordinator.station_id.replace("-", "_")
        self._attr_unique_id = f"{DOMAIN}_{coordinator.station_id}_last_measurement"
        self._attr_translation_key = "last_measurement"
        self._attr_suggested_object_id = f"{station_slug}_last_measurement"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Return last measurement time as datetime."""
        if not self.coordinator.data:
            return None
        dt_str = self.coordinator.data.get("last_measurement")
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes."""
        return {
            "stream": self._coordinator.stream_name,
            "station": self._coordinator.station_name,
        }


class ChmiFloodStatusSensor(ChmiBaseSensor):
    """Numeric flood status sensor (-1 to 4)."""

    def __init__(self, coordinator: ChmiHydrologyCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        station_slug = coordinator.station_id.replace("-", "_")
        self._attr_unique_id = f"{DOMAIN}_{coordinator.station_id}_flood_status"
        self._attr_translation_key = "flood_status"
        self._attr_suggested_object_id = f"{station_slug}_flood_status"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = None

    @property
    def native_value(self) -> int | None:
        """Return numeric flood status (-1 to 4)."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("flood_stage")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return flood thresholds and current evaluation basis."""
        meta = self._coordinator._meta
        spa_typ = meta.get("SPA_TYP", "H")

        if spa_typ == "Q":
            thresholds = {
                "evaluated_by": "flow rate (m³/s)",
                "drought_m3s": meta.get("DRYQ"),
                "spa1_m3s":    meta.get("SPA1Q"),
                "spa2_m3s":    meta.get("SPA2Q"),
                "spa3_m3s":    meta.get("SPA3Q"),
                "spa4_m3s":    meta.get("SPA4Q"),
            }
        else:
            thresholds = {
                "evaluated_by": "water level (cm)",
                "drought_cm":  meta.get("DRYH"),
                "spa1_cm":     meta.get("SPA1H"),
                "spa2_cm":     meta.get("SPA2H"),
                "spa3_cm":     meta.get("SPA3H"),
                "spa4_cm":     meta.get("SPA4H"),
            }

        return {
            "stream":      self._coordinator.stream_name,
            "station":    self._coordinator.station_name,
            "station_id": self._coordinator.station_id,
            **thresholds,
        }


class ChmiFloodStatusDescSensor(ChmiBaseSensor):
    """Text flood status sensor (translation key as value)."""

    def __init__(self, coordinator: ChmiHydrologyCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        station_slug = coordinator.station_id.replace("-", "_")
        self._attr_unique_id = f"{DOMAIN}_{coordinator.station_id}_flood_status_desc"
        self._attr_translation_key = "flood_status_desc"
        self._attr_suggested_object_id = f"{station_slug}_flood_status_desc"

    @property
    def native_value(self) -> str | None:
        """Return translation key of current flood status."""
        if not self.coordinator.data:
            return None
        stage = self.coordinator.data.get("flood_stage")
        if stage is None:
            return None
        return FLOOD_STATUS.get(stage, {}).get("translation_key")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return numeric stage as additional attribute."""
        stage = self.coordinator.data.get("flood_stage") if self.coordinator.data else None
        return {
            "stage":      stage,
            "stream":      self._coordinator.stream_name,
            "station":    self._coordinator.station_name,
            "station_id": self._coordinator.station_id,
        }


# Trend thresholds in cm (or m³/s for Q-type stations) per 30-minute window
# Difference = avg(last 30 min) - avg(previous 30 min)
TREND_LEVELS = [
    ("falling_fast",   None,  -10.0),
    ("falling",        -10.0,  -3.0),
    ("falling_slow",    -3.0,  -1.0),
    ("steady",          -1.0,   1.0),
    ("rising_slow",      1.0,   3.0),
    ("rising",           3.0,  10.0),
    ("rising_fast",     10.0,  None),
]


def _float_history_values(samples: list[dict[str, Any]]) -> list[float]:
    """Parse numeric values from history samples; skip invalid entries."""
    out: list[float] = []
    for h in samples:
        if h.get("value") is None:
            continue
        try:
            out.append(float(h["value"]))
        except (ValueError, TypeError):
            _LOGGER.debug("Skipping invalid trend history value: %r", h.get("value"))
    return out


class ChmiTrendSensor(ChmiBaseSensor):
    """Sensor for water level / flow rate trend over last 30 minutes."""

    def __init__(self, coordinator: ChmiHydrologyCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        station_slug = coordinator.station_id.replace("-", "_")
        self._attr_unique_id = f"{DOMAIN}_{coordinator.station_id}_trend"
        self._attr_translation_key = "trend"
        self._attr_suggested_object_id = f"{station_slug}_trend"

    def _calculate_trend(self) -> tuple[str | None, float | None]:
        """Calculate trend from time series history.

        Compares average of last 30 min vs average of previous 30 min.
        Uses H (water level) for H-type stations, Q for Q-type stations.

        Returns:
            (trend_key, diff) where trend_key is one of the TREND_LEVELS keys.
        """
        if not self.coordinator.data:
            return None, None

        spa_typ = self._coordinator._meta.get("SPA_TYP", "H")
        ts_id = "Q" if spa_typ == "Q" else "H"

        ts_data = self.coordinator.data.get(ts_id)
        if not ts_data:
            return None, None

        history = ts_data.get("history", [])
        if len(history) < 6:  # Need at least 6 x 10min = 60 min of data
            return None, None

        # Last 3 readings = last 30 min (10 min interval)
        recent = _float_history_values(history[-3:])
        # Previous 3 readings = 30–60 min ago
        previous = _float_history_values(history[-6:-3])

        if not recent or not previous:
            return None, None

        diff = sum(recent) / len(recent) - sum(previous) / len(previous)

        for key, low, high in TREND_LEVELS:
            if (low is None or diff >= low) and (high is None or diff < high):
                return key, round(diff, 2)

        return "steady", round(diff, 2)

    @property
    def native_value(self) -> str | None:
        """Return trend translation key."""
        key, _ = self._calculate_trend()
        return key

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return numeric difference and evaluation basis."""
        spa_typ = self._coordinator._meta.get("SPA_TYP", "H")
        key, diff = self._calculate_trend()
        return {
            "stream":          self._coordinator.stream_name,
            "station":        self._coordinator.station_name,
            "station_id":     self._coordinator.station_id,
            "evaluated_by":   "flow rate (m³/s)" if spa_typ == "Q" else "water level (cm)",
            "difference":     diff,
            "window_minutes": 30,
        }
