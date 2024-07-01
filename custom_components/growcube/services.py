from typing import Mapping, Any
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from growcube_client import Channel, WateringMode

from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

from . import GrowcubeDataCoordinator
from .const import DOMAIN, CHANNEL_NAME, SERVICE_WATER_PLANT, SERVICE_SET_WATERING_MODE, ARGS_CHANNEL, ARGS_DURATION, \
    ARGS_MIN_VALUE, ARGS_MAX_VALUE
import logging

_LOGGER = logging.getLogger(__name__)

@callback
async def async_setup_services(hass):

    async def async_call_water_plant_service(service_call: ServiceCall) -> None:
        await _async_handle_water_plant(hass, service_call.data)

    async def async_call_set_watering_mode_service(service_call: ServiceCall) -> None:
        await _async_handle_set_watering_mode(hass, service_call.data)

    hass.services.async_register(DOMAIN,
                                 SERVICE_WATER_PLANT,
                                 async_call_water_plant_service,
                                 schema=vol.Schema(
                                     {
                                         vol.Required(ATTR_DEVICE_ID): cv.string,
                                         vol.Required(ARGS_CHANNEL, default='A'): cv.string,
                                         vol.Required(ARGS_DURATION, default=5): cv.positive_int,
                                     },
                                 ))
    hass.services.async_register(DOMAIN,
                                 SERVICE_SET_WATERING_MODE,
                                 async_call_set_watering_mode_service,
                                 schema=vol.Schema(
                                     {
                                         vol.Required(ATTR_DEVICE_ID): cv.string,
                                         vol.Required(ARGS_CHANNEL, default='A'): cv.string,
                                         vol.Required(ARGS_MIN_VALUE, default=15): cv.positive_int,
                                         vol.Required(ARGS_MAX_VALUE, default=40): cv.positive_int,
                                     }
                                 ))


async def _async_handle_water_plant(hass: HomeAssistant, data: Mapping[str, Any]) -> None:

    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get(data[ATTR_DEVICE_ID])
    device = list(device_entry.identifiers)[0][1]
    coordinator = _get_coordinator(hass, device)

    if coordinator is None:
        _LOGGER.warning(f"Unable to find coordinator for {data[ATTR_DEVICE_ID]}")
        return

    channel_str = data["channel"]
    duration_str = data["duration"]

    # Validate data
    if channel_str not in CHANNEL_NAME:
        _LOGGER.error(
            "%s: %s - Invalid channel specified: %s",
            id,
            SERVICE_WATER_PLANT,
            channel_str
        )
        raise HomeAssistantError(f"Invalid channel '{channel_str}' specified")

    try:
        duration = int(duration_str)
    except ValueError:
        _LOGGER.error(
            "%s: %s - Invalid duration '%s'",
            id,
            SERVICE_WATER_PLANT,
            duration_str
        )
        raise HomeAssistantError(f"Invalid duration '{duration_str} specified'")

    if duration < 1 or duration > 60:
        _LOGGER.error(
            "%s: %s - Invalid duration '%s', should be 1-60",
            id,
            SERVICE_WATER_PLANT,
            duration
        )
        raise HomeAssistantError(f"Invalid duration '{duration}' specified, should be 1-60")

    channel = Channel(CHANNEL_NAME.index(channel_str))

    await coordinator.handle_water_plant(channel, duration)


async def _async_handle_set_watering_mode(hass: HomeAssistant, data: Mapping[str, Any]) -> None:

    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get(data[ATTR_DEVICE_ID])
    device = list(device_entry.identifiers)[0][1]
    coordinator = _get_coordinator(hass, device)

    if coordinator is None:
        _LOGGER.error(f"Unable to find coordinator for {device}")
        return

    channel_str = data["channel"]
    min_value = data["min_value"]
    max_value = data["max_value"]

    # Validate data
    if channel_str not in CHANNEL_NAME:
        _LOGGER.error(
            "%s: %s - Invalid channel specified: %s",
            device,
            SERVICE_SET_WATERING_MODE,
            channel_str
        )
        raise HomeAssistantError(f"Invalid channel '{channel_str}' specified")

    if min_value <= 0 or min_value > 100:
        _LOGGER.error(
            "%s: %s - Invalid min_value specified: %s",
            device,
            SERVICE_SET_WATERING_MODE,
            min_value
        )
        raise HomeAssistantError(f"Invalid min_value '{min_value}' specified")

    if max_value <= 0 or max_value > 100:
        _LOGGER.error(
            "%s: %s - Invalid max_value specified: %s",
            device,
            SERVICE_SET_WATERING_MODE,
            max_value
        )
        raise HomeAssistantError(f"Invalid max_value '{max_value}' specified")

    if max_value <= min_value:
        _LOGGER.error(
            "%s: %s - Invalid values specified, max_value %s must be bigger than min_value %s",
            device,
            SERVICE_SET_WATERING_MODE,
            min_value,
            max_value
        )
        raise HomeAssistantError(
            f"Invalid values specified, max_value {max_value}must be bigger than min_value {min_value}")

    channel = Channel(CHANNEL_NAME.index(channel_str))
    await coordinator.handle_set_watering_mode(channel, min_value, max_value)


def _get_coordinator(hass: HomeAssistant, device: str) -> GrowcubeDataCoordinator:
    for key in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][key]
        if coordinator.data.device_id == device:
            return coordinator

    _LOGGER.error("No coordinator found for %s", device)
    return None