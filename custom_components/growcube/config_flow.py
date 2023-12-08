"""Config flow for the Growcube integration."""
import voluptuous as vol
import asyncio
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_HOST
from growcube_client import GrowcubeClient

from .const import DOMAIN

class GrowcubeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Growcube config flow."""

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""

        if user_input is not None:
            # Validate the user input.
            errors = await self._async_validate_user_input(user_input)
            if not errors:
                # User input is valid, create a new config entry.
                return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)
            else:
                # User input is invalid, show an error message.
                return self._show_error(errors)

        # Show the form to the user.
        return self._async_show_form()

    async def _async_validate_user_input(self, user_input):
        """Validate the user input."""
        errors = {}
        try:
            client = GrowcubeClient(user_input[CONF_HOST], None)
            await asyncio.wait_for(client.connect(), timeout=10)
            client.disconnect()
        except asyncio.TimeoutError:
            errors[CONF_HOST] = "Connection timed out"
        except OSError:
            errors[CONF_HOST] = "Unable to connect to host"

        return errors

    async def _async_show_form(self, errors=None):
        """Show the form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str
            }),
            errors=errors
        )

    async def _async_show_error(self, errors):
        """Show an error message to the user."""
        return await self._async_show_form(errors)