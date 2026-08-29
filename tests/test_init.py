"""Tests for the Growcube integration setup."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_HOST
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.growcube import async_setup_entry


async def test_setup_entry_raises_not_ready_on_handshake_failure(hass):
    """A failed handshake must raise ConfigEntryNotReady so HA retries setup.

    The coordinator must also be disconnected, so no connection or reconnect
    task from the failed attempt can keep occupying the device's single
    client slot.
    """
    entry = MagicMock()
    entry.data = {CONF_HOST: "192.168.1.100"}

    with patch(
        "custom_components.growcube.GrowcubeDataCoordinator"
    ) as mock_coordinator_cls:
        coordinator = mock_coordinator_cls.return_value
        coordinator.connect = AsyncMock(
            return_value=(False, "Timed out waiting for device ID")
        )
        coordinator.disconnect = MagicMock()

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)

        coordinator.disconnect.assert_called_once()
