"""Config flow for the Growcube integration."""
from typing import Optional, Dict, Any

import voluptuous as vol
import asyncio
from homeassistant import config_entries
from homeassistant.components import dhcp
from homeassistant.core import callback
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResult

from . import GrowcubeDataCoordinator
from .const import DOMAIN

DATA_SCHEMA = {
    vol.Required(CONF_HOST): str,
}


class GrowcubeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Growcube config flow."""
    VERSION = 1

    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> FlowResult:
        """Handle DHCP discovery flow."""
        host = discovery_info.ip
        # Validate device by connecting and getting device_id
        result, device_id_or_error = await GrowcubeDataCoordinator.get_device_id(host)
        if not result:
            return self.async_abort(reason="cannot_connect")

        await self.async_set_unique_id(device_id_or_error)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        return self.async_create_entry(title=host, data={CONF_HOST: host})

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle a flow initialized by the user."""

        if not user_input:
            return await self._show_form()

        # Validate the user input.
        errors, device_id = await self._async_validate_user_input(user_input)
        if errors:
            # return self._show_form(errors)
            return await self._show_form(errors)

        await self.async_set_unique_id(device_id)
        self._abort_if_unique_id_configured(updates=user_input)

        return self.async_create_entry(title=user_input[CONF_HOST],
                                       data=user_input)

    async def _async_validate_user_input(self, user_input: dict[str, Any]) -> tuple[Dict[str, str], Optional[str]]:
        """Validate the user input."""
        errors = {}
        device_id = ""
        result, value = await asyncio.wait_for(GrowcubeDataCoordinator.get_device_id(user_input[CONF_HOST]), timeout=4)
        if not result:
            errors[CONF_HOST] = value
        else:
            device_id = value

        return errors, device_id

    async def _show_form(self, errors: dict[str, str] | None = None) -> FlowResult:
        """Show the form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(DATA_SCHEMA),
            errors=errors if errors else {}
        )
