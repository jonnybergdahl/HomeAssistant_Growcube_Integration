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

    sensors = [
        LockedStateSensor(coordinator),
        WaterStateSensor(coordinator),
        PumpLockedStateSensor(coordinator, 0),
        PumpLockedStateSensor(coordinator, 1),
        PumpLockedStateSensor(coordinator, 2),
        PumpLockedStateSensor(coordinator, 3)
    ]

    async_add_entities(sensors, True)


class LockedStateSensor(BinarySensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator):
        self._coordinator = coordinator
        self._coordinator.entities.append(self)
        self._attr_unique_id = f"{coordinator.model.device_id}_locked"
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"
        self._attr_name = f"Device Locked"
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
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("Update device_lock_state %s", self._coordinator.model.device_lock_state)
        self._attr_native_value = self._coordinator.model.device_lock_state
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """When the entity is added to hass."""
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))


class WaterStateSensor(BinarySensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator):
        self._coordinator = coordinator
        self._coordinator.entities.append(self)
        self._attr_unique_id = f"{coordinator.model.device_id}_water_level"
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"
        self._attr_name = f"Water Level"
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
            return "mdi:water"

    @property
    def is_on(self):
        return self._coordinator.model.water_state

    @callback
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("Update water_state %s", self._coordinator.model.water_state)
        self._attr_native_value = self._coordinator.model.water_state
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))


class PumpLockedStateSensor(BinarySensorEntity):
    _channel_name = ['A', 'B', 'C', 'D']
    _channel_id = ['a', 'b', 'c', 'd']

    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        self._coordinator = coordinator
        self._coordinator.entities.append(self)
        self._channel = channel
        self._attr_unique_id = f"{coordinator.model.device_id}_pump_" + self._channel_id[channel] + "_locked"
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"
        self._attr_name = f"Pump " + self._channel_name[channel] + " Locked"
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
    def _handle_coordinator_update(self) -> None:
        _LOGGER.debug("Update pump_lock_state[%s] %s",
                      self._channel,
                      self._coordinator.model.pump_lock_state[self._channel])
        self._attr_native_value = self._coordinator.model.pump_lock_state[self._channel]
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """When the entity is added to hass."""
        self.async_on_remove(self._coordinator.async_add_listener(self._handle_coordinator_update))
