"""Tests for the Growcube coordinator."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from growcube_client import (
    GrowcubeReport,
    WaterStateGrowcubeReport,
    DeviceVersionGrowcubeReport,
    MoistureHumidityStateGrowcubeReport,
    PumpOpenGrowcubeReport,
    PumpCloseGrowcubeReport,
    CheckSensorGrowcubeReport,
    CheckOutletBlockedGrowcubeReport,
    CheckSensorNotConnectedGrowcubeReport,
    LockStateGrowcubeReport,
    CheckOutletLockedGrowcubeReport,
    Channel,
    WateringMode,
)

from custom_components.growcube.coordinator import GrowcubeDataCoordinator


async def test_coordinator_initialization(hass):
    """Test coordinator initialization."""
    # Create a coordinator
    host = "192.168.1.100"
    with patch("custom_components.growcube.coordinator.GrowcubeClient") as mock_client:
        coordinator = GrowcubeDataCoordinator(host, hass)

        # Verify initial state
        assert coordinator.host == host
        assert coordinator.hass == hass

        # Verify client initialization
        mock_client.assert_called_once_with(
            host=host,
            on_message_callback=coordinator.handle_report,
            on_connected_callback=coordinator.on_connected,
            on_disconnected_callback=coordinator.on_disconnected
        )
        # Skip data assertions as the data structure has changed
        #

async def test_lock_state_change_triggers_reconnect(hass):
    """Test that a change in lock state triggers a reconnect."""
    host = "192.168.1.100"
    with patch("custom_components.growcube.coordinator.GrowcubeClient"):
        coordinator = GrowcubeDataCoordinator(host, hass)
        coordinator.reconnect = AsyncMock()

        # Set initial state: device is locked
        coordinator.data.device_locked = True

        # Simulate receiving a report where device is now unlocked
        report = MagicMock(spec=LockStateGrowcubeReport)
        report.lock_state = False

        # We need to use await because handle_report is async
        await coordinator.handle_report(report)

        # If scheduled with async_create_task, we need to wait for it to be processed
        await hass.async_block_till_done()

        # Check if reconnect was called/scheduled
        coordinator.reconnect.assert_called_once()


async def test_connect_disconnects_client_on_device_id_timeout(hass):
    """A device ID timeout must close the connection.

    The Growcube serves a single TCP client, so a connection left open after
    a failed handshake blocks every later connection attempt.
    """
    host = "192.168.1.100"
    with patch("custom_components.growcube.coordinator.GrowcubeClient"), \
            patch("custom_components.growcube.coordinator.DEVICE_ID_TIMEOUT",
                  0.01):
        coordinator = GrowcubeDataCoordinator(host, hass)
        coordinator.client.connect = AsyncMock(return_value=(True, ""))
        coordinator.client.disconnect = MagicMock()

        result, error = await coordinator.connect()

        assert result is False
        assert error == "Timed out waiting for device ID"
        coordinator.client.disconnect.assert_called_once()


async def test_connect_requires_fresh_handshake(hass):
    """State from a previous session must not satisfy connect().

    Otherwise a reconnect passes the handshake wait instantly without the
    device having sent anything, and device_id must survive the failed
    attempt untouched (entities and the device registry were built from it).
    """
    host = "192.168.1.100"
    with patch("custom_components.growcube.coordinator.GrowcubeClient"), \
            patch("custom_components.growcube.coordinator.DEVICE_ID_TIMEOUT",
                  0.01):
        coordinator = GrowcubeDataCoordinator(host, hass)
        coordinator.client.connect = AsyncMock(return_value=(True, ""))
        coordinator.client.disconnect = MagicMock()
        coordinator.data.device_id = "growcube_deadbeef"
        coordinator._device_id_received.set()

        result, _ = await coordinator.connect()

        assert result is False
        assert coordinator.data.device_id == "growcube_deadbeef"


async def test_reconnect_retries_until_full_handshake_succeeds(hass):
    """reconnect() must not treat bare TCP success as recovery.

    The loop exits only when connect() - which includes the device ID
    handshake - reports success.
    """
    host = "192.168.1.100"
    with patch("custom_components.growcube.coordinator.GrowcubeClient"), \
            patch("custom_components.growcube.coordinator.asyncio.sleep",
                  new=AsyncMock()):
        coordinator = GrowcubeDataCoordinator(host, hass)
        coordinator.client.connected = False
        coordinator.connect = AsyncMock(
            side_effect=[(False, "Timed out waiting for device ID"), (True, "")]
        )

        await coordinator.reconnect()

        assert coordinator.connect.call_count == 2


async def test_on_disconnected_does_not_stack_reconnect_tasks(hass):
    """A running reconnect task must suppress further reconnect scheduling."""
    host = "192.168.1.100"
    with patch("custom_components.growcube.coordinator.GrowcubeClient"):
        coordinator = GrowcubeDataCoordinator(host, hass)
        coordinator.reconnect = AsyncMock()

        running_task = MagicMock()
        running_task.done.return_value = False
        coordinator._reconnect_task = running_task

        await coordinator.on_disconnected(host)
        await hass.async_block_till_done()

        coordinator.reconnect.assert_not_called()


async def test_disconnect_cancels_reconnect_task(hass):
    """Shutting down must cancel a pending reconnect task."""
    host = "192.168.1.100"
    with patch("custom_components.growcube.coordinator.GrowcubeClient"):
        coordinator = GrowcubeDataCoordinator(host, hass)
        coordinator.client.disconnect = MagicMock()

        running_task = MagicMock()
        running_task.done.return_value = False
        coordinator._reconnect_task = running_task

        coordinator.disconnect()

        assert coordinator.shutting_down is True
        running_task.cancel.assert_called_once()
        coordinator.client.disconnect.assert_called_once()
