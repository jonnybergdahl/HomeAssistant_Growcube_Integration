from homeassistant.const import EntityCategory, Platform
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant import config_entries
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .coordinator import GrowcubeDataCoordinator
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from .const import DOMAIN, CHANNEL_NAME, CHANNEL_ID
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Growcube sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DeviceLockedSensor(coordinator),
                        WaterWarningSensor(coordinator),
                        PumpOpenStateSensor(coordinator, 0),
                        PumpOpenStateSensor(coordinator, 1),
                        PumpOpenStateSensor(coordinator, 2),
                        PumpOpenStateSensor(coordinator, 3),
                        OutletLockedSensor(coordinator, 0),
                        OutletLockedSensor(coordinator, 1),
                        OutletLockedSensor(coordinator, 2),
                        OutletLockedSensor(coordinator, 3),
                        OutletBlockedSensor(coordinator, 0),
                        OutletBlockedSensor(coordinator, 1),
                        OutletBlockedSensor(coordinator, 2),
                        OutletBlockedSensor(coordinator, 3),
                        SensorFaultSensor(coordinator, 0),
                        SensorFaultSensor(coordinator, 1),
                        SensorFaultSensor(coordinator, 2),
                        SensorFaultSensor(coordinator, 3),
                        SensorDisconnectedSensor(coordinator, 0),
                        SensorDisconnectedSensor(coordinator, 1),
                        SensorDisconnectedSensor(coordinator, 2),
                        SensorDisconnectedSensor(coordinator, 3),
                        ], True)


class DeviceLockedSensor(BinarySensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator):
        super().__init__()
        self._coordinator = coordinator
        self._coordinator.register_device_locked_state_callback(self.update)
        self._attr_unique_id = f"{coordinator.data.device_id}_device_locked"
        self._attr_name = "Device locked"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_is_on = coordinator.data.device_locked

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.device.device_info

    @callback
    def update(self, new_state: bool | None) -> None:
        _LOGGER.debug("%s: Update device_locked %s -> %s",
                      self._coordinator.data.device_id,
                      self._attr_is_on,
                      new_state
                      )
        if new_state != self._attr_is_on:
            self._attr_is_on = new_state
            self.async_write_ha_state()


class WaterWarningSensor(BinarySensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator):
        super().__init__()
        self._coordinator = coordinator
        self._coordinator.register_water_warning_state_callback(self.update)
        self._attr_unique_id = f"{coordinator.data.device_id}_water_warning"
        self._attr_name = "Water warning"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_is_on = coordinator.data.water_warning

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.device.device_info

    @property
    def icon(self) -> str:
        if self._attr_is_on:
            return "mdi:water-alert"
        else:
            return "mdi:water-check"

    @callback
    def update(self, new_state: bool | None) -> None:
        _LOGGER.debug("%s: Update water_state %s -> %s",
                      self._coordinator.data.device_id,
                      self._attr_is_on,
                      new_state
                      )
        if new_state != self._attr_is_on:
            self._attr_is_on = new_state
            self.async_write_ha_state()


class PumpOpenStateSensor(BinarySensorEntity):

    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        super().__init__()
        self._coordinator = coordinator
        self._coordinator.register_pump_open_state_callback(self.update)
        self._channel = channel
        self._attr_unique_id = f"{coordinator.data.device_id}_pump_{CHANNEL_ID[channel]}_open"
        self._attr_name = f"Pump {CHANNEL_NAME[channel]} open"
        self._attr_device_class = BinarySensorDeviceClass.OPENING
        self._attr_is_on = coordinator.data.pump_open[self._channel]
        self._attr_entity_registry_enabled_default = False

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.device.device_info

    @property
    def icon(self) -> str:
        if self._attr_is_on:
            return "mdi:water"
        else:
            return "mdi:water-off"

    @callback
    def update(self, new_state: bool | None) -> None:
        _LOGGER.debug("%s: Update pump_state[%s] %s -> %s",
                      self._coordinator.data.device_id,
                      self._channel,
                      self._attr_is_on,
                      new_state
                      )
        if new_state != self._attr_is_on:
            self._attr_is_on = new_state
            self.async_write_ha_state()


class OutletLockedSensor(BinarySensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        super().__init__()
        self._coordinator = coordinator
        self._coordinator.register_outlet_locked_state_callback(self.update)
        self._channel = channel
        self._attr_unique_id = f"{coordinator.data.device_id}_outlet_{CHANNEL_ID[channel]}_locked"
        self._attr_name = f"Outlet {CHANNEL_NAME[channel]} locked"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_is_on = coordinator.data.outlet_locked_state[self._channel]

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.device.device_info

    @property
    def icon(self) -> str:
        if self._attr_is_on:
            return "mdi:pump-off"
        else:
            return "mdi:pump"

    @callback
    def update(self, new_state: bool | None) -> None:
        _LOGGER.debug("%s: Update pump_lock_state[%s] %s -> %s",
                      self._coordinator.data.device_id,
                      self._channel,
                      self._attr_is_on,
                      new_state
                      )
        if new_state != self._attr_is_on:
            self._attr_is_on = new_state
            self.async_write_ha_state()


class OutletBlockedSensor(BinarySensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        super().__init__()
        self._coordinator = coordinator
        self._coordinator.register_outlet_blocked_state_callback(self.update)
        self._channel = channel
        self._attr_unique_id = f"{coordinator.data.device_id}_outlet_{CHANNEL_ID[channel]}_blocked"
        self._attr_name = f"Outlet {CHANNEL_NAME[channel]} blocked"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_is_on = coordinator.data.outlet_blocked_state[self._channel]

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.device.device_info

    @property
    def icon(self) -> str:
        if self._attr_is_on:
            return "mdi:water-pump-off"
        else:
            return "mdi:water-pump"

    @callback
    def update(self, new_state: bool | None) -> None:
        _LOGGER.debug("%s: Update pump_lock_state[%s] %s -> %s",
                      self._coordinator.data.device_id,
                      self._channel,
                      self._attr_is_on,
                      new_state
                      )
        if new_state != self._attr_is_on:
            self._attr_is_on = new_state
            self.async_write_ha_state()


class SensorFaultSensor(BinarySensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        super().__init__()
        self._coordinator = coordinator
        self._coordinator.register_sensor_fault_state_callback(self.update)
        self._channel = channel
        self._attr_unique_id = f"{coordinator.data.device_id}_sensor_{CHANNEL_ID[channel]}_fault"
        self._attr_name = f"Sensor {CHANNEL_NAME[channel]} fault"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_is_on = coordinator.data.sensor_abnormal[self._channel]

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.device.device_info

    @property
    def icon(self) -> str:
        if self._attr_is_on:
            return "mdi:thermometer-probe-off"
        else:
            return "mdi:thermometer-probe"

    @callback
    def update(self, new_state: bool | None) -> None:
        _LOGGER.debug("%s: Update sensor_state[%s] %s -> %s",
                      self._coordinator.data.device_id,
                      self._channel,
                      self._attr_is_on,
                      new_state
                      )
        if new_state != self._attr_is_on:
            self._attr_is_on = new_state
            self.async_write_ha_state()


class SensorDisconnectedSensor(BinarySensorEntity):
    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        super().__init__()
        self._coordinator = coordinator
        self._coordinator.register_sensor_disconnected_state_callback(self.update)
        self._channel = channel
        self._attr_unique_id = f"{coordinator.data.device_id}_sensor_{CHANNEL_ID[channel]}_disconnected"
        self._attr_name = f"Sensor {CHANNEL_NAME[channel]} disconnected"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_is_on = coordinator.data.sensor_disconnected[self._channel]

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.device.device_info

    @property
    def icon(self) -> str:
        if self._attr_is_on:
            return "mdi:thermometer-probe-off"
        else:
            return "mdi:thermometer-probe"

    @callback
    def update(self, new_state: bool | None) -> None:
        _LOGGER.debug("%s: Update sensor_state[%s] %s -> %s",
                      self._coordinator.data.device_id,
                      self._channel,
                      self._attr_is_on,
                      new_state
                      )
        if new_state != self._attr_is_on:
            self._attr_is_on = new_state
            self.async_write_ha_state()
