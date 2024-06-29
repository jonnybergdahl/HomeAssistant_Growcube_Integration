import asyncio
from datetime import datetime
from typing import Optional, List, Tuple

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
from growcube_client import WateringModeCommand, SyncTimeCommand
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_OK,
    STATE_PROBLEM,
    STATE_LOCKED,
    STATE_OPEN,
    STATE_CLOSED,
)
import logging

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, CHANNEL_NAME

_LOGGER = logging.getLogger(__name__)


class GrowcubeDataModel:
    def __init__(self, host: str):
        # Device
        self.host: str = host
        self.version: str = ""
        self.device_id: Optional[str] = None
        self.device_info: Optional[DeviceInfo] = None

        # Sensors
        self.temperature: Optional[int] = None
        self.humidity: Optional[int] = None
        self.moisture: List[Optional[int]] = [None, None, None, None]
        self.pump_open: List[bool] = [False, False, False, False]

        # Diagnostics
        self.device_locked: int = False
        self.water_warning: int = False
        self.sensor_abnormal: List[int] = [False, False, False, False]
        self.sensor_disconnected: List[int] = [False, False, False, False]
        self.outlet_blocked_state: List[int] = [False, False, False, False]
        self.outlet_locked_state: List[int] = [False, False, False, False]


class GrowcubeDataCoordinator(DataUpdateCoordinator):
    def __init__(self, host: str, hass: HomeAssistant):
        self.client = GrowcubeClient(
            host, self.handle_report, self.on_connected, self.on_disconnected
        )
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.entities = []
        self.device_id = None
        self.data: GrowcubeDataModel = GrowcubeDataModel(host)
        self.shutting_down = False

    def set_device_id(self, device_id: str) -> None:
        self.device_id = hex(int(device_id))[2:]
        self.data.device_id = f"growcube_{self.device_id}"
        self.data.device_info = {
            "name": "GrowCube " + self.device_id,
            "identifiers": {(DOMAIN, self.data.device_id)},
            "manufacturer": "Elecrow",
            "model": "Growcube",
            "sw_version": self.data.version,
        }

    async def _async_update_data(self):
        return self.data

    async def connect(self) -> Tuple[bool, str]:
        result, error = await self.client.connect()
        if not result:
            return False, error

        self.shutting_down = False
        # Wait for the device to send back the DeviceVersionGrowcubeReport
        while not self.data.device_id:
            await asyncio.sleep(0.1)
        _LOGGER.debug(
            "Growcube device id: %s",
            self.data.device_id
        )

        time_command = SyncTimeCommand(datetime.now())
        _LOGGER.debug(
            "%s: Sending SyncTimeCommand",
            self.data.device_id
        )
        self.client.send_command(time_command)
        return True, ""

    @staticmethod
    async def get_device_id(host: str) -> tuple[bool, str]:
        """This is used in the config flow to check for a valid device"""
        device_id = ""

        def _handle_device_id_report(report: GrowcubeReport):
            if isinstance(report, DeviceVersionGrowcubeReport):
                nonlocal device_id
                device_id = report.device_id

        async def _check_device_id_assigned():
            nonlocal device_id
            while not device_id:
                await asyncio.sleep(0.1)

        client = GrowcubeClient(host, _handle_device_id_report)
        result, error = await client.connect()
        if not result:
            return False, error

        try:
            await asyncio.wait_for(_check_device_id_assigned(), timeout = 5)
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
        if self.data.device_id is not None:
            self.hass.states.async_set(
                DOMAIN + "." + self.data.device_id, STATE_UNAVAILABLE
            )
            self.reset_sensor_data()
        if not self.shutting_down:
            _LOGGER.debug(
                "Device host %s went offline, will try to reconnect",
                host
            )
            while not self.shutting_down:
                await asyncio.sleep(10)
                result, error = await self.client.connect()
                if not result:
                    _LOGGER.debug(
                        "Reconnect failed for %s with error '%s', retrying in 10 seconds",
                        host,
                        error)
                else:
                    _LOGGER.debug(
                        "Reconnect to %s succeeded",
                        host
                    )
                    return

    def disconnect(self) -> None:
        self.shutting_down = True
        self.client.disconnect()

    def reset_sensor_data(self) -> None:
        self.data.temperature = None
        self.data.humidity = None
        self.data.moisture = [None, None, None, None]
        self.data.pump_open = [False, False, False, False]
        self.data.device_locked = False
        self.data.water_warning = False
        self.data.sensor_abnormal = [False, False, False, False]
        self.data.sensor_disconnected = [False, False, False, False]
        self.data.outlet_blocked_state = [False, False, False, False]
        self.data.outlet_locked_state = [False, False, False, False]

    def handle_report(self, report: GrowcubeReport):
        """Handle a report from the Growcube."""
        # 24 - RepDeviceVersion
        if isinstance(report, DeviceVersionGrowcubeReport):
            _LOGGER.debug(
                "Device device_id: %s, version %s",
                report.device_id,
                report.version
            )
            self.data.version = report.version
            self.set_device_id(report.device_id)

        # 20 - RepWaterState
        elif isinstance(report, WaterStateGrowcubeReport):
            _LOGGER.debug(
                "%s: Water state %s",
                self.data.device_id,
                report.water_warning
            )
            self.data.water_warning = report.water_warning

        # 21 - RepSTHSate
        elif isinstance(report, MoistureHumidityStateGrowcubeReport):
            _LOGGER.debug(
                "%s: Sensor reading, channel %s, humidity %s, temperature %s, moisture %s",
                self.data.device_id,
                report.channel,
                report.humidity,
                report.temperature,
                report.moisture,
            )
            self.data.humidity = report.humidity
            self.data.temperature = report.temperature
            self.data.moisture[report.channel.value] = report.moisture

        # 26 - RepPumpOpen
        elif isinstance(report, PumpOpenGrowcubeReport):
            _LOGGER.debug(
                "%s: Pump open, channel %s",
                self.data.device_id,
                report.channel
            )
            self.data.pump_open[report.channel.value] = True

        # 27 - RepPumpClose
        elif isinstance(report, PumpCloseGrowcubeReport):
            _LOGGER.debug(
                "%s: Pump closed, channel %s",
                self.data.device_id,
                report.channel
            )
            self.data.pump_open[report.channel.value] = False

        # 28 - RepCheckSenSorNotConnected
        elif isinstance(report, CheckSensorGrowcubeReport):
            _LOGGER.debug(
                "%s: Sensor abnormal, channel %s",
                self.data.device_id,
                report.channel
            )
            self.data.sensor_abnormal[report.channel.value] = True

        # 29 - Pump channel blocked
        elif isinstance(report, CheckOutletBlockedGrowcubeReport):
            _LOGGER.debug(
                "%s: Outlet blocked, channel %s",
                self.data.device_id,
                report.channel
            )
            self.data.outlet_blocked_state[report.channel.value] = True

        # 30 - RepCheckSenSorNotConnect
        elif isinstance(report, CheckSensorNotConnectedGrowcubeReport):
            _LOGGER.debug(
                "%s: Check sensor, channel %s",
                self.data.device_id,
                report.channel
            )
            self.data.sensor_disconnected[report.channel.value] = True
            # self.moisture_sensors[report.channel.value].update(None)

        # 33 - RepLockstate
        elif isinstance(report, LockStateGrowcubeReport):
            _LOGGER.debug(
                f"%s: Lock state, %s",
                self.data.device_id,
                report.lock_state
            )
            self.data.device_lock_state = report.lock_state

        # 34 - ReqCheckSenSorLock
        elif isinstance(report, CheckOutletLockedGrowcubeReport):
            _LOGGER.debug(
                "%s Check outlet, channel %s",
                self.data.device_id,
                report.channel
            )
            self.data.outlet_locked_state[report.channel.value] = True

    async def water_plant(self, channel: int) -> None:
        await self.client.water_plant(Channel(channel), 5)

    async def handle_water_plant(self, call: ServiceCall):
        # Validate channel
        channel_str = call.data.get("channel")
        duration_str = call.data.get("duration")

        # Validate data
        if channel_str not in CHANNEL_NAME:
            _LOGGER.error(
                "%s: Invalid channel specified for water_plant: %s",
                self.data.device_id,
                channel_str
            )
            return

        try:
            duration = int(duration_str)
        except ValueError:
            _LOGGER.error("%s: Invalid duration '%s' for water_plant", self.device_id, duration_str)
            return

        if duration < 1 or duration > 60:
            _LOGGER.error(
                "%s: Invalid duration '%s' for water_plant, should be 1-60",
                self.data.device_id,
                duration
            )
            return

        channel = Channel(CHANNEL_NAME.index(channel_str))

        _LOGGER.debug(
            "%s: Service water_plant called, %s, %s",
            self.data.device_id,
            channel_str,
            duration_str
        )
        await self.client.water_plant(channel, duration)

    async def handle_set_watering_mode(self, call: ServiceCall):
        # Set watering mode
        channel_str = call.data.get("channel")
        min_value = call.data.get("min_value")
        max_value = call.data.get("max_value")
        channel_names = ["A", "B", "C", "D"]

        # Validate data
        if channel_str not in channel_names:
            _LOGGER.error(
                "%s: Invalid channel specified for set_watering_mode: %s",
                self.data.device_id,
                channel_str
            )
            return

        if min_value <= 0 or min_value > 100:
            _LOGGER.error(
                "%s: Invalid value specified for min_value: %s",
                self.data.device_id,
                min_value
            )
            return

        if max_value <= 0 or max_value > 100:
            _LOGGER.error(
                "%sInvalid value specified for max_value: %s",
                self.data.device_id, max_value,
                max_value
            )
            return

        if max_value <= min_value:
            _LOGGER.error(
                "%s: Invalid values specified, max_value must be bigger than min_value",
                self.data.device_id
            )
            return

        channel = Channel(channel_names.index(channel_str))
        command = WateringModeCommand(channel, WateringMode.Smart, min_value, max_value)

        _LOGGER.debug(
            "%s: Service set_watering_mode called, %s, %s, %s",
            self.data.device_id,
            channel_str,
            min_value,
            max_value,
        )
        self.client.send_command(command)
