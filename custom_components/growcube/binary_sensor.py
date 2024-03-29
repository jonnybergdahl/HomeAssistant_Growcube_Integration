from homeassistant.const import EntityCategory, Platform
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from .coordinator import GrowcubeDataCoordinator
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Growcube sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(coordinator.binary_sensors, True)


class LockedStateSensor(BinarySensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator):
        self._coordinator = coordinator
        self._coordinator.entities.append(self)
        self._attr_unique_id = f"{coordinator.model.device_id}_locked"
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"
        self._attr_name = f"Device locked"
        self._attr_device_class = BinarySensorDeviceClass.LOCK
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_value = coordinator.model.device_lock_state

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.model.device_info

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        return not self._coordinator.model.device_lock_state

    @callback
    def update(self, state: bool) -> None:
        _LOGGER.debug("Update device_lock_state %s", state)
        if self._coordinator.model.device_lock_state != state:
            self._coordinator.model.device_lock_state = state
            self._attr_native_value = state
            self.async_write_ha_state()


class WaterStateSensor(BinarySensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator):
        self._coordinator = coordinator
        self._coordinator.entities.append(self)
        self._attr_unique_id = f"{coordinator.model.device_id}_water_level"
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"
        self._attr_name = f"Water level"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_value = coordinator.model.device_lock_state

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.model.device_info

    @property
    def icon(self):
        if self.is_on:
            return "mdi:water-alert"
        else:
            return "mdi:water-check"

    @property
    def is_on(self):
        return self._coordinator.model.water_state

    @callback
    def update(self, state: bool) -> None:
        _LOGGER.debug("Update water_state %s", state)
        if self._coordinator.model.water_state != state:
            self._coordinator.model.water_state = state
            self._attr_native_value = state
            self.async_write_ha_state()

    async def async_added_to_hass(self):
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))


class PumpOpenStateSensor(BinarySensorEntity):
    _channel_name = ['A', 'B', 'C', 'D']
    _channel_id = ['a', 'b', 'c', 'd']

    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        self._coordinator = coordinator
        self._coordinator.entities.append(self)
        self._channel = channel
        self._attr_unique_id = f"{coordinator.model.device_id}_pump_" + self._channel_id[channel] + "_open"
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"
        self._attr_name = f"Pump " + self._channel_name[channel] + " open"
        self._attr_device_class = BinarySensorDeviceClass.OPENING
        self._attr_native_value = coordinator.model.pump_open[self._channel]
        self._attr_entity_registry_enabled_default = False

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.model.device_info

    @property
    def icon(self):
        if self.is_on:
            return "mdi:water"
        else:
            return "mdi:water-off"

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        return self._coordinator.model.pump_open[self._channel]

    @callback
    def update(self, state: bool) -> None:
        _LOGGER.debug("Update pump_state[%s] %s",
                      self._channel,
                      state)
        if self._coordinator.model.pump_open[self._channel] != state:
            self._coordinator.model.pump_open[self._channel] = state
            self._attr_native_value = state
            self.async_write_ha_state()


class PumpLockedStateSensor(BinarySensorEntity):
    _channel_name = ['A', 'B', 'C', 'D']
    _channel_id = ['a', 'b', 'c', 'd']

    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        self._coordinator = coordinator
        self._coordinator.entities.append(self)
        self._channel = channel
        self._attr_unique_id = f"{coordinator.model.device_id}_pump_" + self._channel_id[channel] + "_locked"
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"
        self._attr_name = f"Pump " + self._channel_name[channel] + "lock state"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_value = coordinator.model.pump_lock_state[self._channel]

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.model.device_info

    @property
    def icon(self):
        if self.is_on:
            return "mdi:pump-off"
        else:
            return "mdi:pump"

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        return self._coordinator.model.pump_lock_state[self._channel]

    @callback
    def update(self, state: bool) -> None:
        _LOGGER.debug("Update pump_lock_state[%s] %s",
                      self._channel,
                      self._coordinator.model.pump_lock_state[self._channel])
        if self._coordinator.model.pump_lock_state[self._channel] != state:
            self._coordinator.model.pump_lock_state[self._channel] = state
            self._attr_native_value = state
            self.async_write_ha_state()


class SensorFaultStateSensor(BinarySensorEntity):
    _channel_name = ['A', 'B', 'C', 'D']
    _channel_id = ['a', 'b', 'c', 'd']

    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        self._coordinator = coordinator
        self._coordinator.entities.append(self)
        self._channel = channel
        self._attr_unique_id = f"{coordinator.model.device_id}_sensor_" + self._channel_id[channel] + "_locked"
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"
        self._attr_name = f"Sensor " + self._channel_name[channel] + " state"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_value = coordinator.model.sensor_state[self._channel]

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.model.device_info

    @property
    def icon(self):
        if self.is_on:
            return "mdi:thermometer-probe-off"
        else:
            return "mdi:thermometer-probe"

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        return self._coordinator.model.sensor_state[self._channel]

    @callback
    def update(self, state: bool) -> None:
        _LOGGER.debug("Update sensor_state[%s] %s",
                      self._channel,
                      self._coordinator.model.sensor_state[self._channel])
        if self._coordinator.model.sensor_state[self._channel] != state:
            self._coordinator.model.sensor_state[self._channel] = state
            self._attr_native_value = state
            self.async_write_ha_state()

