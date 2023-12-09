import asyncio
from typing import Optional, List, Tuple

from growcube_client import GrowcubeClient, GrowcubeReport, Channel
from growcube_client import (WaterStateGrowcubeReport,
                             DeviceVersionGrowcubeReport,
                             MoistureHumidityStateGrowcubeReport,
                             PumpOpenGrowcubeReport,
                             PumpCloseGrowcubeReport,
                             CheckSensorGrowcubeReport,
                             CheckPumpBlockedGrowcubeReport,
                             CheckSensorNotConnectedGrowcubeReport,
                             LockStateGrowcubeReport)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import STATE_UNAVAILABLE, STATE_OK, STATE_PROBLEM, STATE_LOCKED, STATE_OPEN, STATE_CLOSED
import logging

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class GrowcubeDataModel:
    def __init__(self, host: str):
        self.host: str = host
        self.version: str = ""
        self.device_id: Optional[str] = None
        self.device_info: Optional[DeviceInfo] = None

        self.temperature: Optional[int] = None
        self.humidity: Optional[int] = None
        self.moisture: List[Optional[int]] = [None, None, None, None]

        self.device_lock_state: int = False
        self.water_state: int = True
        self.sensor_state: List[int] = [True, True, True, True]
        self.pump_lock_state: List[int] = [False, False, False, False]

        self.pump_open: List[bool] = [False, False, False, False]


class GrowcubeDataCoordinator(DataUpdateCoordinator):
    def __init__(self, host: str, hass: HomeAssistant):
        self.client = GrowcubeClient(host, self.handle_report,
                                     self.on_connected,
                                     self.on_disconnected)
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.entities = []
        self.device_id = None
        self.model: GrowcubeDataModel = GrowcubeDataModel(host)

    def set_device_id(self, device_id: str) -> None:
        self.device_id = hex(int(device_id))[2:]
        self.model.device_id = f"growcube_{self.device_id}"
        self.model.device_info = {
            "name": "GrowCube " + self.device_id,
            "identifiers": {(DOMAIN, self.model.device_id)},
            "manufacturer": "Elecrow",
            "model": "GrowCube",
            "sw_version": self.model.version
        }

    async def _async_update_data(self):
        return self.model

    async def connect(self) -> Tuple[bool, str]:
        result, error = await self.client.connect()
        if not result:
            return False, error

        # Wait for the device to send back the DeviceVersionGrowcubeReport
        while not self.model.device_id:
            await asyncio.sleep(0.1)
        _LOGGER.debug("Growcube device id: %s", self.model.device_id)
        return True, ""

    @staticmethod
    async def get_device_id(host: str) -> tuple[bool, str]:
        """ This is used in the config flow to check for a valid device """
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
            await asyncio.wait_for(_check_device_id_assigned(), timeout=2)
            client.disconnect()
        except asyncio.TimeoutError:
            client.disconnect()
            return False, 'Timed out waiting for device ID'

        return True, device_id

    def on_connected(self, host: str) -> None:
        _LOGGER.debug(f"Connection to {host} established")

    def on_disconnected(self, host: str) -> None:
        _LOGGER.debug(f"Connection to {host} lost")
        self.hass.states.async_set(self.model.entity_id, STATE_UNAVAILABLE)

    def disconnect(self) -> None:
        """Disconnect from the Growcube device."""
        self.client.disconnect()

    def handle_report(self, report: GrowcubeReport):
        """Handle a report from the Growcube."""
        if isinstance(report, DeviceVersionGrowcubeReport):
            self.model.version = report.version
            self.set_device_id(report.device_id)
        elif isinstance(report, WaterStateGrowcubeReport):
            self.model.water_state = not report.water_warning
        elif isinstance(report, MoistureHumidityStateGrowcubeReport):
            _LOGGER.debug(f"humidity %s, temperature %s, moisture %s",
                          report.humidity,
                          report.temperature,
                          report.moisture)
            self.model.humidity = report.humidity
            self.model.temperature = report.temperature
            self.model.moisture[report.channel.value] = report.moisture
        elif isinstance(report, PumpOpenGrowcubeReport):
            self.model.pump_open[report.channel.value] = True
        elif isinstance(report, PumpCloseGrowcubeReport):
            self.model.pump_open[report.channel.value] = False
        elif isinstance(report, CheckSensorGrowcubeReport):
            # Investigate this one
            pass
        elif isinstance(report, CheckPumpBlockedGrowcubeReport):
            self.model.pump_lock_state[report.channel.value] = True
        elif isinstance(report, CheckSensorNotConnectedGrowcubeReport):
            self.model.sensor_state[report.channel.value] = True
        elif isinstance(report, LockStateGrowcubeReport):
            self.model.device_lock_state = report.lock_state

        for entity in self.entities:
            entity.async_schedule_update_ha_state(True)

    async def water_plant(self, channel: int) -> None:
        await self.client.water_plant(Channel(channel), 5)

    async def handle_water_plant(self, call: ServiceCall):
        # Validate channel
        channel_str = call.data.get('channel')
        duration_str = call.data.get('duration')
        channel_names = ['A', 'B', 'C', 'D']

        # Validate data
        if channel_str not in channel_names:
            _LOGGER.error("Invalid channel specified for water_plant: %s", channel_str)
            return

        try:
            duration = int(duration_str)
        except ValueError:
            _LOGGER.error("Invalid duration '%s' for water_plant", duration_str)
            return

        if duration < 1 or duration > 60:
            _LOGGER.error("Invalid duration '%s' for water_plant, should be 1-60", duration)
            return

        channel = Channel(channel_names.index(channel_str))

        await self.client.water_plant(channel, duration)