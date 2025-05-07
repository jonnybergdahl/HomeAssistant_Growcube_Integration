"""Fixtures for Growcube integration tests."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.const import CONF_HOST

from custom_components.growcube.const import DOMAIN


@pytest.fixture
def mock_growcube_client():
    """Mock the GrowcubeClient."""
    with patch("custom_components.growcube.coordinator.GrowcubeClient") as mock_client:
        client = mock_client.return_value
        client.connect = AsyncMock(return_value=True)
        client.disconnect = AsyncMock(return_value=True)
        client.send_command = AsyncMock(return_value=True)
        yield client


@pytest.fixture
async def mock_integration(hass: HomeAssistant, mock_growcube_client):
    """Set up the Growcube integration in Home Assistant."""
    # Mock the get_device_id method to return a test device ID
    with patch("custom_components.growcube.coordinator.GrowcubeDataCoordinator.get_device_id", 
               return_value="test_device_id"):

        # Create a mock coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.data.device_id = "test_device_id"
        mock_coordinator.device.device_info = {"identifiers": {(DOMAIN, "test_device_id")}}

        # Set up the mock data structure
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN]["test_entry_id"] = mock_coordinator

        await hass.async_block_till_done()
        yield
