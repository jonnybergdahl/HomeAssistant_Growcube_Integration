"""Support for Growcube sensors."""
from homeassistant.const import PERCENTAGE, UnitOfTemperature, Platform
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.core import callback, HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CHANNEL_ID, CHANNEL_NAME
import logging

from .coordinator import GrowcubeDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Growcube sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TemperatureSensor(coordinator),
                        HumiditySensor(coordinator),
                        MoistureSensor(coordinator, 0),
                        MoistureSensor(coordinator, 1),
                        MoistureSensor(coordinator, 2),
                        MoistureSensor(coordinator, 3)], True)


class TemperatureSensor(SensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator) -> None:
        self._coordinator = coordinator
        self._coordinator.register_temperature_state_callback(self.update)
        self._attr_unique_id = f"{coordinator.data.device_id}_temperature"
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"
        self._attr_native_value = coordinator.data.temperature
        self._attr_name = "Temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_value = None

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.device.device_info

    @callback
    def update(self, new_value: int) -> None:

        _LOGGER.debug(
            "%s: Update temperature %s -> %s",
            self._coordinator.device.device_id,
            self._attr_native_value,
            new_value
        )
        if new_value != self._attr_native_value:
            self._attr_native_value = new_value
            self.async_write_ha_state()


class HumiditySensor(SensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator) -> None:
        self._coordinator = coordinator
        self._coordinator.register_humidity_state_callback(self.update)
        self._attr_unique_id = f"{coordinator.data.device_id}_humidity"
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"
        self._attr_name = "Humidity"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_native_value = None

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.device.device_info

    @callback
    def update(self, new_value: int) -> None:
        _LOGGER.debug(
            "%s: Update humidity %s",
            self._coordinator.data.device_id,
            self._coordinator.data.humidity
        )
        if new_value != self._attr_native_value:
            self._attr_native_value = new_value
            self.async_write_ha_state()


class MoistureSensor(SensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._coordinator.register_moisture_state_callback(self.update)
        self._channel = channel
        self._attr_unique_id = f"{coordinator.data.device_id}_moisture_{CHANNEL_ID[self._channel]}"
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"
        self._attr_name = f"Moisture {CHANNEL_NAME[self._channel]}"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.MOISTURE
        self._attr_native_value = None

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.device.device_info

    @property
    def icon(self) -> str:
        return "mdi:cup-water"

    @callback
    def update(self, new_value: int) -> None:
        _LOGGER.debug(
            "%s: Update moisture[%s] %s",
            self._coordinator.data.device_id,
            self._channel,
            new_value
        )
        if new_value != self._attr_native_value:
            self._attr_native_value = new_value
            self.async_write_ha_state()
