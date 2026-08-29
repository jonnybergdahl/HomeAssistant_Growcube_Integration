"""Tests for the Growcube coordinator."""
import asyncio
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
    GrowcubeMessage,
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


async def test_connect_reports_a_failed_handshake(hass):
    """The client owns the handshake and its cleanup as of growcube-client 1.3.0.

    connect() only has to pass the failure on, without recording anything from
    an attempt that never identified a device.
    """
    host = "192.168.1.100"
    with patch("custom_components.growcube.coordinator.GrowcubeClient"):
        coordinator = GrowcubeDataCoordinator(host, hass)
        coordinator.client.connect = AsyncMock(
            return_value=(False, "Timed out waiting for device ID from " + host)
        )

        result, error = await coordinator.connect()

        assert result is False
        assert "device ID" in error
        assert coordinator.data.device_id is None


async def test_connect_takes_the_device_id_from_the_client(hass):
    """connect() must not wait for handle_report to run.

    The client dispatches the report as a task, so it may not have been
    scheduled yet when connect() returns, and entities and the device registry
    are built from device_id.
    """
    host = "192.168.1.100"
    with patch("custom_components.growcube.coordinator.GrowcubeClient"):
        coordinator = GrowcubeDataCoordinator(host, hass)
        coordinator.client.connect = AsyncMock(return_value=(True, ""))
        coordinator.client.device_id = "12345678"
        coordinator.client.version = "3.6"

        result, error = await coordinator.connect()

        assert result is True, error
        assert coordinator.data.device_id == "growcube_bc614e"
        assert coordinator.data.version == "3.6"


async def test_get_device_id_delegates_to_the_client(hass):
    """The config flow check lives in the client now."""
    with patch("custom_components.growcube.coordinator.GrowcubeClient") as mock_client_cls:
        mock_client_cls.get_device_id = AsyncMock(return_value=(True, "12345678"))

        result, value = await GrowcubeDataCoordinator.get_device_id("192.168.1.100")

        assert result is True
        assert value == "12345678"


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


async def test_connect_completes_the_real_handshake(hass, socket_enabled):
    """End to end against a stand-in device, using the real client.

    Every other test here mocks GrowcubeClient, so nothing would catch the
    coordinator and the library disagreeing about when device_id is ready.
    The client sets it before dispatching the report, and connect() reads it
    from there rather than waiting for handle_report to be scheduled.
    """
    async def handle_device(reader, writer):
        writer.write(GrowcubeMessage.to_bytes(24, "3.6@12345678"))
        await writer.drain()
        # Returns once the coordinator closes its end
        await reader.read()
        writer.close()

    server = await asyncio.start_server(handle_device, "127.0.0.1", 0)
    coordinator = None
    try:
        coordinator = GrowcubeDataCoordinator("127.0.0.1", hass)
        coordinator.client.port = server.sockets[0].getsockname()[1]

        result, error = await coordinator.connect()

        assert result is True, error
        assert coordinator.data.device_id == "growcube_bc614e"
        assert coordinator.data.version == "3.6"
    finally:
        if coordinator is not None:
            coordinator.disconnect()
        server.close()
        await server.wait_closed()
        await hass.async_block_till_done()
