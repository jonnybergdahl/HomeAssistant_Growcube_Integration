import asyncio
from datetime import datetime
from typing import Optional, List, Tuple, Callable
from dataclasses import replace

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


from dataclasses import dataclass, field

@dataclass
class GrowcubeData:
    """Class to hold Growcube data."""
    temperature: Optional[int] = None
    humidity: Optional[int] = None
    moisture: List[Optional[int]] = field(default_factory=lambda: [None] * 4)
    pump_open: List[bool] = field(default_factory=lambda: [False] * 4)
    sensor_fault: List[bool] = field(default_factory=lambda: [False] * 4)
    sensor_disconnected: List[bool] = field(default_factory=lambda: [False] * 4)
    outlet_blocked: List[bool] = field(default_factory=lambda: [False] * 4)
    outlet_locked: List[bool] = field(default_factory=lambda: [False] * 4)
    water_warning: bool = False
    device_locked: bool = False
    device_id: Optional[str] = None
    version: Optional[str] = None
    device_info: Optional[DeviceInfo] = None


class GrowcubeDataCoordinator(DataUpdateCoordinator[GrowcubeData]):
    def __init__(self, host: str, hass: HomeAssistant):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.client = GrowcubeClient(
            host=host,
            on_message_callback=self.handle_report,
            on_connected_callback=self.on_connected,
            on_disconnected_callback=self.on_disconnected,
        )
        self.host = host
        self.data = GrowcubeData()
        self.shutting_down = False

    def set_device_id(self, device_id: str) -> None:
        id_str = hex(int(device_id))[2:]
        self.data.device_id = "growcube_{}".format(id_str)
        self.data.device_info = DeviceInfo(
            name="GrowCube " + id_str,
            identifiers={(DOMAIN, self.data.device_id)},
            manufacturer="Elecrow",
            model="Growcube",
            sw_version=self.data.version,
        )
        self.async_set_updated_data(self.data)

    async def connect(self) -> Tuple[bool, str]:
        result, error = await self.client.connect()
        if not result:
            return False, error

        self.shutting_down = False
        # Wait for the device to send back the DeviceVersionGrowcubeReport
        retries = 50
        while not self.data.device_id and retries > 0:
            retries -= 1
            await asyncio.sleep(0.1)

        if not self.data.device_id:
            return False, "Timed out waiting for device ID"

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

        async def _handle_device_id_report(report: GrowcubeReport) -> None:
            if isinstance(report, DeviceVersionGrowcubeReport):
                nonlocal device_id
                device_id = report.device_id

        async def _check_device_id_assigned() -> None:
            nonlocal device_id
            while not device_id:
                await asyncio.sleep(0.1)

        client = GrowcubeClient(
            host=host,
            on_message_callback=_handle_device_id_report,
        )
        try:
            result, error = await asyncio.wait_for(client.connect(), timeout=5)
        except asyncio.TimeoutError:
            return False, "Timed out connecting to device"
        if not result:
            return False, error

        try:
            await asyncio.wait_for(_check_device_id_assigned(), timeout=5)
            client.disconnect()
        except asyncio.TimeoutError:
            client.disconnect()
            return False, "Timed out waiting for device ID"

        return True, device_id

    async def on_connected(self, host: str) -> None:
        _LOGGER.debug(
            "Connection to %s established",
            host
        )

    async def on_disconnected(self, host: str) -> None:
        _LOGGER.debug("Connection to %s lost", host)
        self.data.temperature = None
        self.data.humidity = None
        self.data.moisture = [None] * 4
        self.data.pump_open = [False] * 4
        self.data.sensor_fault = [False] * 4
        self.data.sensor_disconnected = [False] * 4
        self.data.outlet_blocked = [False] * 4
        self.data.outlet_locked = [False] * 4
        self.data.water_warning = False
        self.data.device_locked = False
        self.async_set_updated_data(self.data)

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

    async def handle_report(self, report: GrowcubeReport) -> None:
        new: GrowcubeData = self.data

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
            return
        # 20 - RepWaterState
        elif isinstance(report, WaterStateGrowcubeReport):
            _LOGGER.debug(
                "%s: Water state %s",
                self.data.device_id,
                report.water_warning
            )
            new = self._set_scalar(new, "water_warning", report.water_warning)
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
            new = self._set_scalar(new, "temperature", report.temperature)
            new = self._set_scalar(new, "humidity", report.humidity)
            new = self._set_list_index(new, "moisture", report.channel.value, report.moisture)
        # 26 - RepPumpOpen
        elif isinstance(report, PumpOpenGrowcubeReport):
            _LOGGER.debug(
                "%s: Pump open, channel %s",
                self.data.device_id,
                report.channel
            )
            new = self._set_list_index(new, "pump_open", report.channel.value, True)
        # 27 - RepPumpClose
        elif isinstance(report, PumpCloseGrowcubeReport):
            _LOGGER.debug(
                "%s: Pump closed, channel %s",
                self.data.device_id,
                report.channel
            )
            new = self._set_list_index(new, "pump_open", report.channel, False)
        # 28 - RepCheckSenSorNotConnected
        elif isinstance(report, CheckSensorGrowcubeReport):
            _LOGGER.debug(
                "%s: Sensor abnormal, channel %s",
                self.data.device_id,
                report.channel
            )
            new = self._set_list_index(new, "sensor_fault", report.channel, True)
        # 29 - Pump channel blocked
        elif isinstance(report, CheckOutletBlockedGrowcubeReport):
            _LOGGER.debug(
                "%s: Outlet blocked, channel %s",
                self.data.device_id,
                report.channel
            )
            new = self._set_list_index(new, "outlet_blocked", report.channel, True)
        # 30 - RepCheckSenSorNotConnect
        elif isinstance(report, CheckSensorNotConnectedGrowcubeReport):
            _LOGGER.debug(
                "%s: Check sensor, channel %s",
                self.data.device_id,
                report.channel
            )
            new = self._set_list_index(new, "sensor_disconnected", report.channel, True)
        # 33 - RepLockstate
        elif isinstance(report, LockStateGrowcubeReport):
            _LOGGER.debug(
                "%s: Lock state, %s",
                self.data.device_id,
                report.lock_state
            )
            # Handle case where the button on the device was pressed, this should do a reconnect
            # to read any problems still present
            if self.data.device_locked and not report.lock_state:
                self.hass.async_create_task(self.reconnect())
            new = self._set_scalar(new, "device_locked", report.lock_state)
        # 34 - ReqCheckSenSorLock
        elif isinstance(report, CheckOutletLockedGrowcubeReport):
            _LOGGER.debug(
                "%s Check outlet, channel %s",
                self.data.device_id,
                report.channel
            )
            new = self._set_list_index(new, "outlet_locked", report.channel, True)

        if new is not self.data:
            self.data = new
            self.async_set_updated_data(new)


    async def water_plant(self, channel: int) -> None:
        await self.client.water_plant(Channel(channel), 5)


    async def handle_water_plant(self, channel: Channel, duration: int) -> None:
        _LOGGER.debug(
            "%s: Service water_plant called, %s, %s",
            self.data.device_id,
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
            self.data.device_id,
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
            self.data.device_id,
            channel,
            duration,
            interval,
        )

        command = WateringModeCommand(channel, WateringMode.Manual, interval, duration)
        self.client.send_command(command)

    async def handle_delete_watering(self, channel: Channel) -> None:

        _LOGGER.debug(
            "%s: Service delete_watering called, %s,",
            self.data.device_id,
            channel
        )
        command = PlantEndCommand(channel)
        self.client.send_command(command)
        command = ClosePumpCommand(channel)
        self.client.send_command(command)

    def _set_scalar(self, new: GrowcubeData, attr: str, value) -> GrowcubeData:
        if getattr(self.data, attr) == value:
            return new
        return replace(new, **{attr: value})

    def _set_list_index(self,
        new: GrowcubeData,
        attr: str,
        idx: int,
        value,
    ) -> GrowcubeData:
        current_list = getattr(self.data, attr)
        if current_list[idx] == value:
            return new
        copied = list(getattr(new, attr))  # copy from `new` (which may already be replaced)
        copied[idx] = value
        return replace(new, **{attr: copied})