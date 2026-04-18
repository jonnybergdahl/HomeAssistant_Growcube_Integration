"""Tests for Growcube services."""
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import ATTR_DEVICE_ID
from custom_components.growcube.const import (
    DOMAIN,
    SERVICE_WATER_PLANT,
    SERVICE_SET_SMART_WATERING,
    SERVICE_SET_SCHEDULED_WATERING,
    SERVICE_DELETE_WATERING,
    ARGS_CHANNEL,
    ARGS_DURATION,
    ARGS_MIN_MOISTURE,
    ARGS_MAX_MOISTURE,
    ARGS_ALL_DAY,
    ARGS_INTERVAL,
)
from custom_components.growcube.services import async_setup_services
from custom_components.growcube.coordinator import GrowcubeDataCoordinator
from growcube_client import Channel

@pytest.fixture
def mock_coordinator(hass: HomeAssistant):
    """Mock a coordinator and add it to hass.data."""
    coordinator = MagicMock(spec=GrowcubeDataCoordinator)
    coordinator.data = MagicMock()
    coordinator.data.device_id = "test_device_serial"
    
    coordinator.handle_water_plant = AsyncMock()
    coordinator.handle_set_smart_watering = AsyncMock()
    coordinator.handle_set_manual_watering = AsyncMock()
    coordinator.handle_delete_watering = AsyncMock()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["test_entry_id"] = coordinator
    return coordinator

@pytest.fixture
async def setup_services(hass: HomeAssistant):
    """Set up the services for testing."""
    await async_setup_services(hass)
    yield

@pytest.fixture
def mock_device_registry(hass: HomeAssistant):
    """Mock the device registry."""
    with patch("homeassistant.helpers.device_registry.async_get") as mock_async_get:
        mock_registry = MagicMock()
        mock_async_get.return_value = mock_registry
        
        # Setup a mock device
        mock_device = MagicMock()
        mock_device.identifiers = {(DOMAIN, "test_device_serial")}
        mock_registry.async_get.return_value = mock_device
        
        yield mock_registry

async def test_water_plant_service(hass: HomeAssistant, setup_services, mock_device_registry, mock_coordinator):
    """Test the water_plant service."""
    # Test success
    await hass.services.async_call(
        DOMAIN,
        SERVICE_WATER_PLANT,
        {
            ATTR_DEVICE_ID: "test_device_id",
            ARGS_CHANNEL: "A",
            ARGS_DURATION: 5,
        },
        blocking=True,
    )
    mock_coordinator.handle_water_plant.assert_called_once_with(Channel.Channel_A, 5)

    # Test invalid channel
    with pytest.raises(HomeAssistantError, match="Invalid channel 'E' specified"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_WATER_PLANT,
            {
                ATTR_DEVICE_ID: "test_device_id",
                ARGS_CHANNEL: "E",
                ARGS_DURATION: 5,
            },
            blocking=True,
        )

    # Test invalid duration (too low)
    with pytest.raises(HomeAssistantError, match="Invalid duration '0' specified, should be 1-60"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_WATER_PLANT,
            {
                ATTR_DEVICE_ID: "test_device_id",
                ARGS_CHANNEL: "A",
                ARGS_DURATION: 0,
            },
            blocking=True,
        )

    # Test invalid duration (too high)
    with pytest.raises(HomeAssistantError, match="Invalid duration '61' specified, should be 1-60"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_WATER_PLANT,
            {
                ATTR_DEVICE_ID: "test_device_id",
                ARGS_CHANNEL: "A",
                ARGS_DURATION: 61,
            },
            blocking=True,
        )

async def test_set_smart_watering_service(hass: HomeAssistant, setup_services, mock_device_registry, mock_coordinator):
    """Test the set_smart_watering service."""
    # Test success
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_SMART_WATERING,
        {
            ATTR_DEVICE_ID: "test_device_id",
            ARGS_CHANNEL: "B",
            ARGS_MIN_MOISTURE: 20,
            ARGS_MAX_MOISTURE: 50,
            ARGS_ALL_DAY: True,
        },
        blocking=True,
    )
    mock_coordinator.handle_set_smart_watering.assert_called_once_with(Channel.Channel_B, True, 20, 50)

    # Test invalid moisture values (min > max)
    with pytest.raises(HomeAssistantError, match="Invalid values specified, max_moisture 20 must be bigger than min_moisture 30"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_SMART_WATERING,
            {
                ATTR_DEVICE_ID: "test_device_id",
                ARGS_CHANNEL: "B",
                ARGS_MIN_MOISTURE: 30,
                ARGS_MAX_MOISTURE: 20,
                ARGS_ALL_DAY: True,
            },
            blocking=True,
        )

async def test_set_scheduled_watering_service(hass: HomeAssistant, setup_services, mock_device_registry, mock_coordinator):
    """Test the set_scheduled_watering service."""
    # Test success
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_SCHEDULED_WATERING,
        {
            ATTR_DEVICE_ID: "test_device_id",
            ARGS_CHANNEL: "C",
            ARGS_DURATION: 10,
            ARGS_INTERVAL: 4,
        },
        blocking=True,
    )
    mock_coordinator.handle_set_manual_watering.assert_called_once_with(Channel.Channel_C, 10, 4)

async def test_delete_watering_service(hass: HomeAssistant, setup_services, mock_device_registry, mock_coordinator):
    """Test the delete_watering service."""
    # Test success
    await hass.services.async_call(
        DOMAIN,
        SERVICE_DELETE_WATERING,
        {
            ATTR_DEVICE_ID: "test_device_id",
            ARGS_CHANNEL: "D",
        },
        blocking=True,
    )
    mock_coordinator.handle_delete_watering.assert_called_once_with(Channel.Channel_D)

async def test_coordinator_not_found(hass: HomeAssistant, setup_services, mock_device_registry):
    """Test when coordinator is not found."""
    # Ensure no coordinator is in hass.data
    hass.data[DOMAIN] = {}
    
    # For _async_handle_water_plant it just logs a warning and returns
    with patch("custom_components.growcube.services._LOGGER") as mock_logger:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_WATER_PLANT,
            {
                ATTR_DEVICE_ID: "test_device_id",
                ARGS_CHANNEL: "A",
                ARGS_DURATION: 5,
            },
            blocking=True,
        )
        mock_logger.warning.assert_called_once()

    # For _async_handle_delete_watering it raises HomeAssistantError
    with pytest.raises(HomeAssistantError, match="Unable to find coordinator for test_device_id"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DELETE_WATERING,
            {
                ATTR_DEVICE_ID: "test_device_id",
                ARGS_CHANNEL: "A",
            },
            blocking=True,
        )
