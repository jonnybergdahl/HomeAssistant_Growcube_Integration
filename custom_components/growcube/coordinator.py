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

from .binary_sensor import LockedStateSensor, WaterStateSensor, SensorFaultStateSensor, PumpLockedStateSensor, \
    PumpOpenStateSensor
from .const import DOMAIN
from .sensor import TemperatureSensor, HumiditySensor, MoistureSensor

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
        self.sensor_state: List[int] = [False, False, False, False]
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

        self.locked_state_sensor = LockedStateSensor(self)
        self.water_state_sensor = WaterStateSensor(self)
        self.pump_open_sensors = [
            PumpOpenStateSensor(self, 0),
            PumpOpenStateSensor(self, 1),
            PumpOpenStateSensor(self, 2),
            PumpOpenStateSensor(self, 3)
        ]
        self.sensor_fault_state_sensors = [
            SensorFaultStateSensor(self, 0),
            SensorFaultStateSensor(self, 1),
            SensorFaultStateSensor(self, 2),
            SensorFaultStateSensor(self, 3)
        ]
        self.pump_locked_state_sensors = [
            PumpLockedStateSensor(self, 0),
            PumpLockedStateSensor(self, 1),
            PumpLockedStateSensor(self, 2),
            PumpLockedStateSensor(self, 3)
        ]
        self.binary_sensors = [
            self.locked_state_sensor,
            self.water_state_sensor,
            self.pump_open_sensors[0],
            self.pump_open_sensors[1],
            self.pump_open_sensors[2],
            self.pump_open_sensors[3],
            self.sensor_fault_state_sensors[0],
            self.sensor_fault_state_sensors[1],
            self.sensor_fault_state_sensors[2],
            self.sensor_fault_state_sensors[3],
            self.pump_locked_state_sensors[0],
            self.pump_locked_state_sensors[1],
            self.pump_locked_state_sensors[2],
            self.pump_locked_state_sensors[3],
        ]

        self.temperature_sensor = TemperatureSensor(self)
        self.humidity_sensor = HumiditySensor(self)
        self.moisture_sensors = [
            MoistureSensor(self, 0),
            MoistureSensor(self, 1),
            MoistureSensor(self, 2),
            MoistureSensor(self, 3),
        ]
        self.sensors = [
            self.temperature_sensor,
            self.humidity_sensor,
            self.moisture_sensors[0],
            self.moisture_sensors[1],
            self.moisture_sensors[2],
            self.moisture_sensors[3],
        ]

    def set_device_id(self, device_id: str) -> None:
        self.device_id = hex(int(device_id))[2:]
        self.model.device_id = f"growcube_{self.device_id}"
        self.model.device_info = {
            "name": "GrowCube " + self.device_id,
            "identifiers": {(DOMAIN, self.model.device_id)},
            "manufacturer": "Elecrow",
            "model": "Growcube",
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
            _LOGGER.debug(f"Device device_id: {report.device_id}, version {report.version}")
            self.model.version = report.version
            self.set_device_id(report.device_id)
        elif isinstance(report, WaterStateGrowcubeReport):
            _LOGGER.debug(f"Water state {report.water_warning}")
            self.water_state_sensor.update(not report.water_warning)
        elif isinstance(report, MoistureHumidityStateGrowcubeReport):
            _LOGGER.debug(f"Sensor reading, channel %s, humidity %s, temperature %s, moisture %s",
                          report.channel,
                          report.humidity,
                          report.temperature,
                          report.moisture)
            self.humidity_sensor.update(report.humidity)
            self.temperature_sensor.update(report.temperature)
            self.moisture_sensors[report.channel.value].update(report.moisture)
        elif isinstance(report, PumpOpenGrowcubeReport):
            _LOGGER.debug(f"Pump open, channel {report.channel}")
            self.pump_open_sensors[report.channel.value].update(True)
        elif isinstance(report, PumpCloseGrowcubeReport):
            _LOGGER.debug(f"Pump closed, channel {report.channel}")
            self.pump_open_sensors[report.channel.value].update(False)
        elif isinstance(report, CheckSensorGrowcubeReport):
            # Investigate this one
            pass
        elif isinstance(report, CheckPumpBlockedGrowcubeReport):
            _LOGGER.debug(f"Pump blocked, channel {report.channel}")
            self.pump_locked_state_sensors[report.channel].update(True)
        elif isinstance(report, CheckSensorNotConnectedGrowcubeReport):
            _LOGGER.debug(f"Check sensor, channel {report.channel}")
            self.sensor_fault_state_sensors[report.channel.value].update(True)
            self.moisture_sensors[report.channel.value].update(None)
        elif isinstance(report, LockStateGrowcubeReport):
            _LOGGER.debug(f"Lock state, {report.lock_state}")
            self.locked_state_sensor.update(report.lock_state)
            self.model.device_lock_state = report.lock_state
            if not report.lock_state:
                # Reset all lock states
                self.model.sensor_state[0].update(False)
                self.model.sensor_state[1].update(False)
                self.model.sensor_state[2].update(False)
                self.model.sensor_state[3].update(False)
                self.model.pump_lock_state[0].update(False)
                self.model.pump_lock_state[1].update(False)
                self.model.pump_lock_state[2].update(False)
                self.model.pump_lock_state[3].update(False)

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