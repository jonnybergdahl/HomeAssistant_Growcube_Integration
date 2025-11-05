import asyncio
from datetime import datetime
from typing import Optional, List, Tuple, Callable

from growcube_client import GrowcubeClient, GrowcubeReport, Channel, WateringMode
from growcube_client import (
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
)
from growcube_client import WateringModeCommand, SyncTimeCommand, PlantEndCommand, ClosePumpCommand
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    STATE_UNAVAILABLE
)
import logging

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class GrowcubeDeviceModel:
    def __init__(self, host: str):
        # Device
        self.host: str = host
        self.version: str = ""
        self.device_id: Optional[str] = None
        self.device_info: Optional[DeviceInfo] = None



class GrowcubeDataCoordinator(DataUpdateCoordinator):
    def __init__(self, host: str, hass: HomeAssistant):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.client = GrowcubeClient(
            host, self.handle_report, self.on_connected, self.on_disconnected
        )
        self.device_id = None
        self.device: GrowcubeDeviceModel = GrowcubeDeviceModel(host)
        self.shutting_down = False
        self._device_locked = False
        self._device_locked_callback: Callable[[bool], None] | None = None
        self._water_warning_callback: Callable[[bool], None] | None = None
        self._pump_open_callbacks: dict[int, Callable[[bool], None]] = {}
        self._outlet_locked_callbacks: dict[int, Callable[[bool], None]] = {}
        self._outlet_blocked_callbacks: dict[int, Callable[[bool], None]] = {}
        self._sensor_fault_callbacks: dict[int, Callable[[bool], None]] = {}
        self._sensor_disconnected_callbacks: dict[int, Callable[[bool], None]] = {}
        self._temperature_value_callback: Callable[[int | None], None] | None = None
        self._humidity_value_callback: Callable[[int | None], None] | None = None
        self._moisture_value_callbacks: dict[int, Callable[[bool | None], None]] = {}

    def set_device_id(self, device_id: str) -> None:
        self.device_id = hex(int(device_id))[2:]
        self.device.device_id = "growcube_{}".format(self.device_id)
        self.device.device_info = {
            "name": "GrowCube " + self.device_id,
            "identifiers": {(DOMAIN, self.device.device_id)},
            "manufacturer": "Elecrow",
            "model": "Growcube",
            "sw_version": self.device.version,
        }

    async def connect(self) -> Tuple[bool, str]:
        result, error = await self.client.connect()
        if not result:
            return False, error

        self.shutting_down = False
        # Wait for the device to send back the DeviceVersionGrowcubeReport
        while not self.device_id:
            await asyncio.sleep(0.1)
        _LOGGER.debug(
            "Growcube device id: %s",
            self.device_id
        )

        time_command = SyncTimeCommand(datetime.now())
        _LOGGER.debug(
            "%s: Sending SyncTimeCommand",
            self.device_id
        )
        self.client.send_command(time_command)
        return True, ""

    async def reconnect(self) -> None:
        if self.client.connected:
            self.client.disconnect()

        if not self.shutting_down:
            while True:
                # Set flag to avoid handling in on_disconnected
                self.shutting_down = True
                result, error = await self.client.connect()
                if result:
                    _LOGGER.debug(
                        "Reconnect to %s succeeded",
                        self.client.host
                    )
                    self.shutting_down = False
                    await asyncio.sleep(10)
                    return

                _LOGGER.debug(
                    "Reconnect failed for %s with error '%s', retrying in 10 seconds",
                    self.client.host,
                    error)
                await asyncio.sleep(10)

    @staticmethod
    async def get_device_id(host: str) -> tuple[bool, str]:
        """This is used in the config flow to check for a valid device"""
        device_id = ""

        def _handle_device_id_report(report: GrowcubeReport) -> None:
            if isinstance(report, DeviceVersionGrowcubeReport):
                nonlocal device_id
                device_id = report.device_id

        async def _check_device_id_assigned() -> None:
            nonlocal device_id
            while not device_id:
                await asyncio.sleep(0.1)

        client = GrowcubeClient(host, _handle_device_id_report)
        result, error = await client.connect()
        if not result:
            return False, error

        try:
            await asyncio.wait_for(_check_device_id_assigned(), timeout=5)
            client.disconnect()
        except asyncio.TimeoutError:
            client.disconnect()
            return False, "Timed out waiting for device ID"

        return True, device_id

    def on_connected(self, host: str) -> None:
        _LOGGER.debug(
            "Connection to %s established",
            host
        )

    async def on_disconnected(self, host: str) -> None:
        _LOGGER.debug("Connection to %s lost", host)
        if self.device.device_id is not None:
            self.hass.states.async_set(
                DOMAIN + "." + self.device.device_id, STATE_UNAVAILABLE
            )
            self.reset_sensor_data()
        if not self.shutting_down:
            _LOGGER.debug(
                "Device host %s went offline, will try to reconnect",
                host
            )
            loop = asyncio.get_event_loop()
            loop.call_later(10, lambda: loop.create_task(self.reconnect()))

    def disconnect(self) -> None:
        self.shutting_down = True
        self.client.disconnect()

    def reset_sensor_data(self) -> None:
        if self._device_locked_callback is not None:
            self._device_locked_callback(False)
        if self._water_warning_callback is not None:
            self._water_warning_callback(False)
        if self._pump_open_callbacks[0] is not None:
            self._pump_open_callbacks[0](False)
        if self._pump_open_callbacks[1] is not None:
            self._pump_open_callbacks[1](False)
        if self._pump_open_callbacks[2] is not None:
            self._pump_open_callbacks[2](False)
        if self._pump_open_callbacks[3] is not None:
            self._pump_open_callbacks[3](False)
        if self._outlet_locked_callbacks[0] is not None:
            self._outlet_locked_callbacks[0](False)
        if self._outlet_locked_callbacks[1] is not None:
            self._outlet_locked_callbacks[1](False)
        if self._outlet_locked_callbacks[2] is not None:
            self._outlet_locked_callbacks[2](False)
        if self._outlet_locked_callbacks[3] is not None:
            self._outlet_locked_callbacks[3](False)
        if self._outlet_blocked_callbacks[0] is not None:
            self._outlet_blocked_callbacks[0](False)
        if self._outlet_blocked_callbacks[1] is not None:
            self._outlet_blocked_callbacks[1](False)
        if self._outlet_blocked_callbacks[2] is not None:
            self._outlet_blocked_callbacks[2](False)
        if self._outlet_blocked_callbacks[3] is not None:
            self._outlet_blocked_callbacks[3](False)
        if self._sensor_fault_callbacks[0] is not None:
            self._sensor_fault_callbacks[0](False)
        if self._sensor_fault_callbacks[1] is not None:
            self._sensor_fault_callbacks[1](False)
        if self._sensor_fault_callbacks[2] is not None:
            self._sensor_fault_callbacks[2](False)
        if self._sensor_fault_callbacks[3] is not None:
            self._sensor_fault_callbacks[3](False)
        if self._sensor_disconnected_callbacks[0] is not None:
            self._sensor_disconnected_callbacks[0](False)
        if self._sensor_disconnected_callbacks[1] is not None:
            self._sensor_disconnected_callbacks[1](False)
        if self._sensor_disconnected_callbacks[2] is not None:
            self._sensor_disconnected_callbacks[2](False)
        if self._sensor_disconnected_callbacks[3] is not None:
            self._sensor_disconnected_callbacks[3](False)
        if self._temperature_value_callback is not None:
            self._temperature_value_callback(None)
        if self._humidity_value_callback is not None:
            self._humidity_value_callback(None)
        if self._moisture_value_callbacks[0] is not None:
            self._moisture_value_callbacks[0](None)
        if self._moisture_value_callbacks[1] is not None:
            self._moisture_value_callbacks[1](None)
        if self._moisture_value_callbacks[2] is not None:
            self._moisture_value_callbacks[2](None)
        if self._moisture_value_callbacks[3] is not None:
            self._moisture_value_callbacks[3](None)

    def register_device_locked_state_callback(self, callback: Callable[[bool], None]) -> None:
        self._device_locked_callback = callback

    def register_water_warning_state_callback(self, callback: Callable[[bool], None]) -> None:
        self._water_warning_callback = callback

    def register_pump_open_state_callback(self, channel: int, callback: Callable[[bool], None]) -> None:
        self._pump_open_callbacks[channel] = callback

    def register_outlet_locked_state_callback(self, channel: int, callback: Callable[[bool], None]) -> None:
        self._outlet_locked_callbacks[channel] = callback

    def register_outlet_blocked_state_callback(self, channel: int, callback: Callable[[bool], None]) -> None:
        self._outlet_blocked_callbacks[channel] = callback

    def register_sensor_fault_state_callback(self, channel: int, callback: Callable[[bool], None]) -> None:
        self._sensor_fault_callbacks[channel] = callback

    def register_sensor_disconnected_state_callback(self, channel: int, callback: Callable[[bool], None]) -> None:
        self._sensor_disconnected_callbacks[channel] = callback

    def register_temperature_state_callback(self, callback: Callable[[int], None]) -> None:
        self._temperature_value_callback = callback

    def register_humidity_state_callback(self, callback: Callable[[int], None]) -> None:
        self._humidity_value_callback = callback

    def register_moisture_state_callback(self, channel: int, callback: Callable[[int], None]) -> None:
        self._moisture_value_callbacks[channel] = callback

    def unregister_device_locked_state_callback(self) -> None:
        self._device_locked_callback = None

    def unregister_water_warning_state_callback(self) -> None:
        self._water_warning_callback = None

    def unregister_pump_open_state_callback(self, channel: int) -> None:
       self._pump_open_callbacks.pop(channel)

    def unregister_outlet_locked_state_callback(self, channel: int, callback: Callable[[bool], None]) -> None:
        self._outlet_locked_callbacks.pop(channel)

    def unregister_outlet_blocked_state_callback(self, channel: int, callback: Callable[[bool], None]) -> None:
        self._outlet_blocked_callbacks.pop(channel)

    def unregister_sensor_fault_state_callback(self, channel: int, callback: Callable[[bool], None]) -> None:
        self._sensor_fault_callbacks.pop(channel)

    def unregister_sensor_disconnected_state_callback(self, channel: int, callback: Callable[[bool], None]) -> None:
        self._sensor_disconnected_callbacks.pop(channel)

    def unregister_temperature_state_callback(self, callback: Callable[[int], None]) -> None:
        self._temperature_value_callback = None

    def unregister_humidity_state_callback(self, callback: Callable[[int], None]) -> None:
        self._humidity_value_callback = None

    def unregister_moisture_state_callback(self, channel: int, callback: Callable[[int], None]) -> None:
        self._moisture_value_callbacks.pop(channel)

    def handle_report(self, report: GrowcubeReport) -> None:
        """Handle a report from the Growcube."""
        # 24 - RepDeviceVersion
        if isinstance(report, DeviceVersionGrowcubeReport):
            _LOGGER.debug(
                "Device device_id: %s, version %s",
                report.device_id,
                report.version
            )
            self.reset_sensor_data()
            self.device.version = report.version
            self.set_device_id(report.device_id)
        # 20 - RepWaterState
        elif isinstance(report, WaterStateGrowcubeReport):
            _LOGGER.debug(
                "%s: Water state %s",
                self.device_id,
                report.water_warning
            )
            if self._water_warning_callback is not None:
                self._water_warning_callback(report.water_warning)
        # 21 - RepSTHSate
        elif isinstance(report, MoistureHumidityStateGrowcubeReport):
            _LOGGER.debug(
                "%s: Sensor reading, channel %s, humidity %s, temperature %s, moisture %s",
                self.device_id,
                report.channel,
                report.humidity,
                report.temperature,
                report.moisture,
            )
            if self._temperature_value_callback is not None:
                self._temperature_value_callback(report.temperature)
            if self._humidity_value_callback is not None:
                self._humidity_value_callback(report.humidity)
            if report.channel.value in self._moisture_value_callbacks:
                self._moisture_value_callbacks[report.channel.value](report.moisture)
        # 26 - RepPumpOpen
        elif isinstance(report, PumpOpenGrowcubeReport):
            _LOGGER.debug(
                "%s: Pump open, channel %s",
                self.device_id,
                report.channel
            )
            if report.channel.value in self._pump_open_callbacks:
                self._pump_open_callbacks[report.channel.value](True)
        # 27 - RepPumpClose
        elif isinstance(report, PumpCloseGrowcubeReport):
            _LOGGER.debug(
                "%s: Pump closed, channel %s",
                self.device_id,
                report.channel
            )
            if report.channel.value in self._pump_open_callbacks:
                self._pump_open_callbacks[report.channel.value](False)
        # 28 - RepCheckSenSorNotConnected
        elif isinstance(report, CheckSensorGrowcubeReport):
            _LOGGER.debug(
                "%s: Sensor abnormal, channel %s",
                self.device_id,
                report.channel
            )
            if report.channel.value in self._sensor_fault_callbacks:
                self._sensor_fault_callbacks[report.channel.value](True)
        # 29 - Pump channel blocked
        elif isinstance(report, CheckOutletBlockedGrowcubeReport):
            _LOGGER.debug(
                "%s: Outlet blocked, channel %s",
                self.device_id,
                report.channel
            )
            if report.channel.value in self._outlet_blocked_callbacks:
                self._outlet_blocked_callbacks[report.channel.value](True)
        # 30 - RepCheckSenSorNotConnect
        elif isinstance(report, CheckSensorNotConnectedGrowcubeReport):
            _LOGGER.debug(
                "%s: Check sensor, channel %s",
                self.device_id,
                report.channel
            )
            if report.channel.value in self._sensor_disconnected_callbacks:
                self._sensor_disconnected_callbacks[report.channel.value](True)
        # 33 - RepLockstate
        elif isinstance(report, LockStateGrowcubeReport):
            _LOGGER.debug(
                "%s: Lock state, %s",
                self.device_id,
                report.lock_state
            )
            # Handle case where the button on the device was pressed, this should do a reconnect
            # to read any problems still present
            if not report.lock_state:
                self.reset_sensor_data()
                self.reconnect()
            if self._device_locked_callback is not None:
                self._device_locked_callback(report.lock_state)
        # 34 - ReqCheckSenSorLock
        elif isinstance(report, CheckOutletLockedGrowcubeReport):
            _LOGGER.debug(
                "%s Check outlet, channel %s",
                self.device_id,
                report.channel
            )
            if report.channel.value in self._outlet_locked_callbacks:
                self._outlet_locked_callbacks[report.channel.value](True)

    async def water_plant(self, channel: int) -> None:
        await self.client.water_plant(Channel(channel), 5)

    async def handle_water_plant(self, channel: Channel, duration: int) -> None:
        _LOGGER.debug(
            "%s: Service water_plant called, %s, %s",
            self.device_id,
            channel,
            duration
        )
        await self.client.water_plant(channel, duration)

    async def handle_set_smart_watering(self, channel: Channel,
                                        all_day: bool,
                                        min_moisture: int,
                                        max_moisture: int) -> None:

        _LOGGER.debug(
            "%s: Service set_smart_watering called, %s, %s, %s, %s",
            self.device_id,
            channel,
            all_day,
            min_moisture,
            max_moisture,
        )

        watering_mode = WateringMode.Smart if all_day else WateringMode.SmartOutside
        command = WateringModeCommand(channel, watering_mode, min_moisture, max_moisture)
        self.client.send_command(command)

    async def handle_set_manual_watering(self, channel: Channel, duration: int, interval: int) -> None:

        _LOGGER.debug(
            "%s: Service set_manual_watering called, %s, %s, %s",
            self.device_id,
            channel,
            duration,
            interval,
        )

        command = WateringModeCommand(channel, WateringMode.Manual, interval, duration)
        self.client.send_command(command)

    async def handle_delete_watering(self, channel: Channel) -> None:

        _LOGGER.debug(
            "%s: Service delete_watering called, %s,",
            self.device_id,
            channel
        )
        command = PlantEndCommand(channel)
        self.client.send_command(command)
        command = ClosePumpCommand(channel)
        self.client.send_command(command)
