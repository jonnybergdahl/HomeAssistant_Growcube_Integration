from homeassistant.components.button import ButtonEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from .coordinator import GrowcubeDataCoordinator
from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]

    buttons = [
        WaterPlantButton(coordinator, 0),
        WaterPlantButton(coordinator, 1),
        WaterPlantButton(coordinator, 2),
        WaterPlantButton(coordinator, 3)
    ]

    async_add_entities(buttons)


class WaterPlantButton(ButtonEntity):
    _channel_name = ['A', 'B', 'C', 'D']
    _channel_id = ['a', 'b', 'c', 'd']

    def __init__(self, coordinator: GrowcubeDataCoordinator, channel: int) -> None:
        self._coordinator = coordinator
        self._channel = channel
        self._attr_name = f"Water plant {self._channel_name[channel]}"
        self._attr_unique_id = f"{coordinator.data.device_id}_water_plant_{self._channel_id[channel]}"
        self.entity_id = f"{Platform.SENSOR}.{self._attr_unique_id}"

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._coordinator.data.device_info

    @property
    def icon(self) -> str:
        return "mdi:watering-can"

    async def async_press(self) -> None:
        await self._coordinator.water_plant(self._channel)
