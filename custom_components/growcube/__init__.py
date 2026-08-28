"""The Growcube integration."""
import asyncio
from homeassistant.const import CONF_HOST, Platform
from homeassistant import config_entries
from homeassistant.exceptions import ConfigEntryNotReady
from .coordinator import GrowcubeDataCoordinator
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .services import async_setup_services

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Set up the Growcube entry."""
    hass.data.setdefault(DOMAIN, {})

    host_name = entry.data[CONF_HOST]
    data_coordinator = GrowcubeDataCoordinator(host_name, hass)
    try:
        connected, error = await data_coordinator.connect()
    except asyncio.TimeoutError as exception:
        raise ConfigEntryNotReady(
            f"Connection to {host_name} timed out"
        ) from exception
    except OSError as exception:
        raise ConfigEntryNotReady(
            f"Unable to connect to host {host_name}: {exception}"
        ) from exception

    if not connected:
        # connect() already closed the client on a handshake timeout; this
        # call additionally sets shutting_down and cancels a reconnect task
        # that a racing on_disconnected may have spawned, so no orphan
        # reconnect loop survives the failed setup.
        data_coordinator.disconnect()
        raise ConfigEntryNotReady(f"Unable to connect to {host_name}: {error}")

    hass.data[DOMAIN][entry.entry_id] = data_coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_setup_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Unload the Growcube entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.disconnect()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
