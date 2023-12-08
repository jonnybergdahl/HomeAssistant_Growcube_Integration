"""Support for Growcube sensors."""
from homeassistant.const import TEMP_CELSIUS, PERCENTAGE, UnitOfTemperature, Platform
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
import logging

from .coordinator import GrowcubeDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Growcube sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        TemperatureSensor(coordinator),
        HumiditySensor(coordinator),
        MoistureSensor(coordinator, 0),
        MoistureSensor(coordinator, 1),
        MoistureSensor(coordinator, 2),
        MoistureSensor(coordinator, 3),
    ]

    async_add_entities(sensors, True)


class TemperatureSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator):
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._coordinator.entities.append(self)
        self._attr_unique_id = f"{coordinator.model.device_id}" + "_temperature"
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"
        self._attr_native_value = coordinator.model.temperature
        self._attr_name = "Temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.model.device_info

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("Update temperature %s", self._coordinator.model.temperature)
        self._attr_native_value = self._coordinator.model.temperature
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """When the entity is added to hass."""
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))


class HumiditySensor(SensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator) -> None:
        self._coordinator = coordinator
        self._coordinator.entities.append(self)
        self._attr_unique_id = f"{coordinator.model.device_id}" + "_humidity"
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"
        self._attr_native_value = coordinator.model.humidity
        self._attr_name = "Humidity"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.HUMIDITY

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.model.device_info

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("Update humidity %s", self._coordinator.model.humidity)
        self._attr_native_value = self._coordinator.model.humidity
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """When the entity is added to hass."""
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))

class MoistureSensor(SensorEntity):
    _channel_name = ['A', 'B', 'C', 'D']
    _channel_id = ['a', 'b', 'c', 'd']

    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._coordinator.entities.append(self)
        self._channel = channel
        self._attr_unique_id = f"{coordinator.model.device_id}" + "_moisture_" + self._channel_id[self._channel]
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"
        self._attr_name = "Moisture " + self._channel_name[self._channel]
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.MOISTURE
        self._attr_native_value = coordinator.model.moisture[self._channel]

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.model.device_info

    @property
    def icon(self):
        return "mdi:waves"

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("Update moisture %s", self._coordinator.model.moisture[self._channel])
        self._attr_native_value = self._coordinator.model.moisture[self._channel]
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """When the entity is added to hass."""
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))
