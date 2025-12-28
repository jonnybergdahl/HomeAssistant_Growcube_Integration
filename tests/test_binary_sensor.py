"""Tests for the Growcube binary sensor platform."""
import pytest
from unittest.mock import patch, MagicMock, call

from homeassistant.const import EntityCategory, Platform
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.growcube.const import DOMAIN, CHANNEL_ID, CHANNEL_NAME
from custom_components.growcube.binary_sensor import (
    DeviceLockedSensor,
    WaterWarningSensor,
    PumpOpenStateSensor,
    OutletLockedSensor,
    OutletBlockedSensor,
    SensorFaultSensor,
    SensorDisconnectedSensor,
)


async def test_device_locked_sensor(hass, mock_growcube_client):
    """Test the device locked sensor."""
    # Create a mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data.device_id = "test_device_id"
    mock_coordinator.data.device_locked = False
    mock_coordinator.data.device_info = {"identifiers": {("test", "test_id")}}

    # Create sensor
    sensor = DeviceLockedSensor(mock_coordinator)

    # Verify sensor properties
    assert sensor.unique_id == "test_device_id_device_locked"
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC

    # Test update with new value
    mock_coordinator.data.device_locked = True
    assert sensor.is_on is True

    # Test update with new value again
    mock_coordinator.data.device_locked = False
    assert sensor.is_on is False


async def test_water_warning_sensor(hass, mock_growcube_client):
    """Test the water warning sensor."""
    # Create a mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data.device_id = "test_device_id"
    mock_coordinator.data.water_warning = False
    mock_coordinator.data.device_info = {"identifiers": {("test", "test_id")}}

    # Create sensor
    sensor = WaterWarningSensor(mock_coordinator)

    # Verify sensor properties
    assert sensor.unique_id == "test_device_id_water_warning"
    assert sensor.device_class == BinarySensorDeviceClass.PROBLEM
    assert sensor.icon == "mdi:water-check"

    # Test update with new value
    mock_coordinator.data.water_warning = True
    assert sensor.is_on is True
    assert sensor.icon == "mdi:water-alert"

    # Test update with new value again
    mock_coordinator.data.water_warning = False
    assert sensor.is_on is False
    assert sensor.icon == "mdi:water-check"


async def test_pump_open_state_sensor(hass, mock_growcube_client):
    """Test the pump open state sensor."""
    # Create a mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data.device_id = "test_device_id"
    mock_coordinator.data.pump_open = [False] * 4
    mock_coordinator.data.device_info = {"identifiers": {("test", "test_id")}}

    # Create sensor for channel 0
    channel = 0
    sensor = PumpOpenStateSensor(mock_coordinator, channel)

    # Verify sensor properties
    assert sensor.unique_id == f"test_device_id_pump_{CHANNEL_ID[channel]}_open"
    assert sensor.icon == "mdi:water-off"

    # Test update with new value
    mock_coordinator.data.pump_open[channel] = True
    assert sensor.is_on is True
    assert sensor.icon == "mdi:water"

    # Test update with new value again
    mock_coordinator.data.pump_open[channel] = False
    assert sensor.is_on is False
    assert sensor.icon == "mdi:water-off"


async def test_outlet_locked_sensor(hass, mock_growcube_client):
    """Test the outlet locked sensor."""
    # Create a mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data.device_id = "test_device_id"
    mock_coordinator.data.outlet_locked = [False] * 4
    mock_coordinator.data.device_info = {"identifiers": {("test", "test_id")}}

    # Create sensor for channel 0
    channel = 0
    sensor = OutletLockedSensor(mock_coordinator, channel)

    # Verify sensor properties
    assert sensor.unique_id == f"test_device_id_outlet_{CHANNEL_ID[channel]}_locked"
    assert sensor.icon == "mdi:pump"
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC

    # Test update with new value
    mock_coordinator.data.outlet_locked[channel] = True
    assert sensor.is_on is True
    assert sensor.icon == "mdi:pump-off"

    # Test update with new value again
    mock_coordinator.data.outlet_locked[channel] = False
    assert sensor.is_on is False
    assert sensor.icon == "mdi:pump"


async def test_outlet_blocked_sensor(hass, mock_growcube_client):
    """Test the outlet blocked sensor."""
    # Create a mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data.device_id = "test_device_id"
    mock_coordinator.data.outlet_blocked = [False] * 4
    mock_coordinator.data.device_info = {"identifiers": {("test", "test_id")}}

    # Create sensor for channel 0
    channel = 0
    sensor = OutletBlockedSensor(mock_coordinator, channel)

    # Verify sensor properties
    assert sensor.unique_id == f"test_device_id_outlet_{CHANNEL_ID[channel]}_blocked"
    assert sensor.icon == "mdi:water-pump"
    assert sensor.device_class == BinarySensorDeviceClass.PROBLEM

    # Test update with new value
    mock_coordinator.data.outlet_blocked[channel] = True
    assert sensor.is_on is True
    assert sensor.icon == "mdi:water-pump-off"

    # Test update with new value again
    mock_coordinator.data.outlet_blocked[channel] = False
    assert sensor.is_on is False
    assert sensor.icon == "mdi:water-pump"


async def test_sensor_fault_sensor(hass, mock_growcube_client):
    """Test the sensor fault sensor."""
    # Create a mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data.device_id = "test_device_id"
    mock_coordinator.data.sensor_fault = [False] * 4
    mock_coordinator.data.device_info = {"identifiers": {("test", "test_id")}}

    # Create sensor for channel 0
    channel = 0
    sensor = SensorFaultSensor(mock_coordinator, channel)

    # Verify sensor properties
    assert sensor.unique_id == f"test_device_id_sensor_{CHANNEL_ID[channel]}_fault"
    assert sensor.icon == "mdi:thermometer-probe"
    assert sensor.device_class == BinarySensorDeviceClass.PROBLEM

    # Test update with new value
    mock_coordinator.data.sensor_fault[channel] = True
    assert sensor.is_on is True
    assert sensor.icon == "mdi:thermometer-probe-off"

    # Test update with new value again
    mock_coordinator.data.sensor_fault[channel] = False
    assert sensor.is_on is False
    assert sensor.icon == "mdi:thermometer-probe"


async def test_sensor_disconnected_sensor(hass, mock_growcube_client):
    """Test the sensor disconnected sensor."""
    # Create a mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data.device_id = "test_device_id"
    mock_coordinator.data.sensor_disconnected = [False] * 4
    mock_coordinator.data.device_info = {"identifiers": {("test", "test_id")}}

    # Create sensor for channel 0
    channel = 0
    sensor = SensorDisconnectedSensor(mock_coordinator, channel)

    # Verify sensor properties
    assert sensor.unique_id == f"test_device_id_sensor_{CHANNEL_ID[channel]}_disconnected"
    assert sensor.icon == "mdi:thermometer-probe"
    assert sensor.device_class == BinarySensorDeviceClass.PROBLEM

    # Test update with new value
    mock_coordinator.data.sensor_disconnected[channel] = True
    assert sensor.is_on is True
    assert sensor.icon == "mdi:thermometer-probe-off"

    # Test update with new value again
    mock_coordinator.data.sensor_disconnected[channel] = False
    assert sensor.is_on is False
    assert sensor.icon == "mdi:thermometer-probe"


async def test_binary_sensor_setup(hass, mock_integration):
    """Test binary sensor setup through the integration."""
    # Import the setup entry function
    from custom_components.growcube.binary_sensor import async_setup_entry

    # Create a mock entry and coordinator
    mock_entry = MagicMock()
    mock_coordinator = MagicMock()
    mock_add_entities = MagicMock()

    # Set up the mock data structure
    hass.data[DOMAIN] = {mock_entry.entry_id: mock_coordinator}

    # Call the setup function
    await async_setup_entry(hass, mock_entry, mock_add_entities)

    # Verify that async_add_entities was called with the correct entities
    assert mock_add_entities.call_count == 1

    # Get the entities that were added
    entities = mock_add_entities.call_args[0][0]

    # Verify that we have the expected number of entities
    # 1 device locked, 1 water warning, 4 pump open, 4 outlet locked, 4 outlet blocked, 4 sensor fault, 4 sensor disconnected
    assert len(entities) == 22

    # Verify the types of entities
    assert isinstance(entities[0], DeviceLockedSensor)
    assert isinstance(entities[1], WaterWarningSensor)

    # Check that we have the right number of each type of channel-specific sensor
    pump_open_sensors = [e for e in entities if isinstance(e, PumpOpenStateSensor)]
    outlet_locked_sensors = [e for e in entities if isinstance(e, OutletLockedSensor)]
    outlet_blocked_sensors = [e for e in entities if isinstance(e, OutletBlockedSensor)]
    sensor_fault_sensors = [e for e in entities if isinstance(e, SensorFaultSensor)]
    sensor_disconnected_sensors = [e for e in entities if isinstance(e, SensorDisconnectedSensor)]

    assert len(pump_open_sensors) == 4
    assert len(outlet_locked_sensors) == 4
    assert len(outlet_blocked_sensors) == 4
    assert len(sensor_fault_sensors) == 4
    assert len(sensor_disconnected_sensors) == 4
