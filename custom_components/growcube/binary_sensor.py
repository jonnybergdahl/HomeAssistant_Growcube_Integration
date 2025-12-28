from homeassistant.const import EntityCategory, Platform
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant import config_entries
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .coordinator import GrowcubeDataCoordinator
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
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
                        ])


class DeviceLockedSensor(CoordinatorEntity[GrowcubeDataCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "device_locked"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: GrowcubeDataCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.device_id}_device_locked"
        self._attr_device_info = coordinator.data.device_info

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.device_locked


class WaterWarningSensor(CoordinatorEntity[GrowcubeDataCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "water_warning"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: GrowcubeDataCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.device_id}_water_warning"
        self._attr_device_info = coordinator.data.device_info

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.water_warning

    @property
    def icon(self) -> str:
        return "mdi:water-alert" if self.is_on else "mdi:water-check"


class PumpOpenStateSensor(CoordinatorEntity[GrowcubeDataCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.OPENING
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._attr_name = f"Pump {CHANNEL_NAME[channel]} open"
        self._attr_unique_id = f"{coordinator.data.device_id}_pump_{CHANNEL_ID[channel]}_open"
        self._attr_device_info = coordinator.data.device_info

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.pump_open[self._channel]

    @property
    def icon(self) -> str:
        return "mdi:water" if self.is_on else "mdi:water-off"


class OutletLockedSensor(CoordinatorEntity[GrowcubeDataCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._attr_name = f"Outlet {CHANNEL_NAME[channel]} locked"
        self._attr_unique_id = f"{coordinator.data.device_id}_outlet_{CHANNEL_ID[channel]}_locked"
        self._attr_device_info = coordinator.data.device_info

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.outlet_locked[self._channel]

    @property
    def icon(self) -> str:
        return "mdi:pump-off" if self.is_on else "mdi:pump"


class OutletBlockedSensor(CoordinatorEntity[GrowcubeDataCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._attr_name = f"Outlet {CHANNEL_NAME[channel]} blocked"
        self._attr_unique_id = f"{coordinator.data.device_id}_outlet_{CHANNEL_ID[channel]}_blocked"
        self._attr_device_info = coordinator.data.device_info

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.outlet_blocked[self._channel]

    @property
    def icon(self) -> str:
        return "mdi:water-pump-off" if self.is_on else "mdi:water-pump"


class SensorFaultSensor(CoordinatorEntity[GrowcubeDataCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._attr_name = f"Sensor {CHANNEL_NAME[channel]} fault"
        self._attr_unique_id = f"{coordinator.data.device_id}_sensor_{CHANNEL_ID[channel]}_fault"
        self._attr_device_info = coordinator.data.device_info

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.sensor_fault[self._channel]

    @property
    def icon(self) -> str:
        return "mdi:thermometer-probe-off" if self.is_on else "mdi:thermometer-probe"


class SensorDisconnectedSensor(CoordinatorEntity[GrowcubeDataCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._attr_name = f"Sensor {CHANNEL_NAME[channel]} disconnected"
        self._attr_unique_id = f"{coordinator.data.device_id}_sensor_{CHANNEL_ID[channel]}_disconnected"
        self._attr_device_info = coordinator.data.device_info

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.sensor_disconnected[self._channel]

    @property
    def icon(self) -> str:
        return "mdi:thermometer-probe-off" if self.is_on else "mdi:thermometer-probe"
