"""Tests for the Growcube sensor platform."""
import pytest
from unittest.mock import patch, MagicMock, call

from homeassistant.const import PERCENTAGE, UnitOfTemperature, Platform
from homeassistant.components.sensor import SensorDeviceClass

from custom_components.growcube.const import DOMAIN, CHANNEL_ID, CHANNEL_NAME
from custom_components.growcube.sensor import (
    TemperatureSensor,
    HumiditySensor,
    MoistureSensor,
)


async def test_sensor_creation(hass, mock_growcube_client):
    """Test creation of sensor entities."""
    # Create a mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data.device_id = "test_device_id"
    mock_coordinator.data.temperature = 25
    mock_coordinator.data.humidity = 50
    mock_coordinator.device.device_info = {"identifiers": {("test", "test_id")}}

    # Create sensors
    temp_sensor = TemperatureSensor(mock_coordinator)
    humidity_sensor = HumiditySensor(mock_coordinator)
    moisture_sensor_0 = MoistureSensor(mock_coordinator, 0)

    # Verify temperature sensor properties
    assert temp_sensor.unique_id == "test_device_id_temperature"
    assert temp_sensor.name == "Temperature"
    assert temp_sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS
    assert temp_sensor.device_class == SensorDeviceClass.TEMPERATURE

    # Verify humidity sensor properties
    assert humidity_sensor.unique_id == "test_device_id_humidity"
    assert humidity_sensor.name == "Humidity"
    assert humidity_sensor.native_unit_of_measurement == PERCENTAGE
    assert humidity_sensor.device_class == SensorDeviceClass.HUMIDITY

    # Verify moisture sensor properties
    assert moisture_sensor_0.unique_id == f"test_device_id_moisture_{CHANNEL_ID[0]}"
    assert moisture_sensor_0.name == f"Moisture {CHANNEL_NAME[0]}"
    assert moisture_sensor_0.native_unit_of_measurement == PERCENTAGE
    assert moisture_sensor_0.device_class == SensorDeviceClass.MOISTURE
    assert moisture_sensor_0.icon == "mdi:cup-water"


async def test_temperature_sensor_update(hass, mock_growcube_client):
    """Test temperature sensor update."""
    # Create a mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data.device_id = "test_device_id"

    # Create temperature sensor
    temp_sensor = TemperatureSensor(mock_coordinator)
    temp_sensor.async_write_ha_state = MagicMock()

    # Test update with new value
    temp_sensor.update(25)
    assert temp_sensor.native_value == 25
    temp_sensor.async_write_ha_state.assert_called_once()

    # Test update with same value (should not trigger state update)
    temp_sensor.async_write_ha_state.reset_mock()
    temp_sensor.update(25)
    assert temp_sensor.native_value == 25
    temp_sensor.async_write_ha_state.assert_not_called()

    # Test update with new value again
    temp_sensor.update(30)
    assert temp_sensor.native_value == 30
    temp_sensor.async_write_ha_state.assert_called_once()


async def test_humidity_sensor_update(hass, mock_growcube_client):
    """Test humidity sensor update."""
    # Create a mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data.device_id = "test_device_id"

    # Create humidity sensor
    humidity_sensor = HumiditySensor(mock_coordinator)
    humidity_sensor.async_write_ha_state = MagicMock()

    # Test update with new value
    humidity_sensor.update(50)
    assert humidity_sensor.native_value == 50
    humidity_sensor.async_write_ha_state.assert_called_once()

    # Test update with same value (should not trigger state update)
    humidity_sensor.async_write_ha_state.reset_mock()
    humidity_sensor.update(50)
    assert humidity_sensor.native_value == 50
    humidity_sensor.async_write_ha_state.assert_not_called()

    # Test update with new value again
    humidity_sensor.update(60)
    assert humidity_sensor.native_value == 60
    humidity_sensor.async_write_ha_state.assert_called_once()


async def test_moisture_sensor_update(hass, mock_growcube_client):
    """Test moisture sensor update."""
    # Create a mock coordinator
    mock_coordinator = MagicMock()
    mock_coordinator.data.device_id = "test_device_id"

    # Create moisture sensor
    moisture_sensor = MoistureSensor(mock_coordinator, 0)
    moisture_sensor.async_write_ha_state = MagicMock()

    # Test update with new value
    moisture_sensor.update(30)
    assert moisture_sensor.native_value == 30
    moisture_sensor.async_write_ha_state.assert_called_once()

    # Test update with same value (should not trigger state update)
    moisture_sensor.async_write_ha_state.reset_mock()
    moisture_sensor.update(30)
    assert moisture_sensor.native_value == 30
    moisture_sensor.async_write_ha_state.assert_not_called()

    # Test update with new value again
    moisture_sensor.update(40)
    assert moisture_sensor.native_value == 40
    moisture_sensor.async_write_ha_state.assert_called_once()
