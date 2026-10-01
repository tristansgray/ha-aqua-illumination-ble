from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, REVOLUTIONS_PER_MINUTE

from . import AxisEntity


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    c = entry.runtime_data
    async_add_entities([FlowSensor(c, "flow"), RpmSensor(c, "rpm")])


class FlowSensor(AxisEntity, SensorEntity):
    _attr_name = "Flow"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    @property
    def native_value(self) -> float:
        return self.coordinator.data[0] / 10


class RpmSensor(AxisEntity, SensorEntity):
    _attr_name = "Speed"
    _attr_native_unit_of_measurement = REVOLUTIONS_PER_MINUTE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        return self.coordinator.data[1]
