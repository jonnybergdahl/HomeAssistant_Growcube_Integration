"""The Growcube integration."""
import asyncio
import logging

from homeassistant.const import CONF_HOST, Platform
from .coordinator import GrowcubeDataCoordinator
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry

_LOGGER = logging.getLogger(__name__)

from .const import *

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: dict):
    """Set up the Growcube entry."""
    hass.data.setdefault(DOMAIN, {})

    host_name = entry.data[CONF_HOST]
    data_coordinator = GrowcubeDataCoordinator(host_name, hass)
    try:
        await data_coordinator.connect()
        hass.data[DOMAIN][entry.entry_id] = data_coordinator

        # Wait for device to report id
        while not data_coordinator.device_id:
            await asyncio.sleep(0.1)

    except asyncio.TimeoutError:
        _LOGGER.error("Connection timed out")
        return False
    except OSError:
        _LOGGER.error("Unable to connect to host")
        return False

    registry = device_registry.async_get(hass)
    device_entry = registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, data_coordinator.data.device_id)},
        name=f"GrowCube " + data_coordinator.device_id,
        manufacturer="Elecrow",
        model="GrowCube",
        sw_version=data_coordinator.data.version
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    hass.services.async_register(DOMAIN,
                                 f"growcube_{data_coordinator.device_id}_water_plant",
                                 data_coordinator.handle_water_plant)
    hass.services.async_register(DOMAIN,
                                 f"growcube_{data_coordinator.device_id}_set_watering_mode",
                                 data_coordinator.handle_set_watering_mode)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: dict):
    """Unload the Growcube entry."""
    client = hass.data[DOMAIN][entry.entry_id]
    client.disconnect()
    return True




