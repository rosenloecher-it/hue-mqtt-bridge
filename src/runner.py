import asyncio
import logging
import signal
import threading

from src.hue.hue_bridge import HueBridge
from src.mqtt.mqtt_proxy import MqttProxy

_logger = logging.getLogger(__name__)


class Runner:

    CONNECTION_TIMEOUT = 5  # seconds

    def __init__(self, hue_bridge: HueBridge, mqtt_proxy: MqttProxy):

        self._hue_bridge = hue_bridge
        self._mqtt_proxy = mqtt_proxy

        self._shutdown = False

        if threading.current_thread() is threading.main_thread():
            # integration tests may run the service in a thread...
            signal.signal(signal.SIGINT, self._signal_shutdown)
            signal.signal(signal.SIGTERM, self._signal_shutdown)

    def _signal_shutdown(self, sig, _frame):
        _logger.info("shutdown signaled (%s)", sig)
        self._shutdown = True

    async def run(self):
        """endless loop"""

        await self._wait_for_mqtt_connection()
        await self._wait_for_hue_connection()

        try:
            while not self._shutdown:

                # Publish queued device state => MQTT
                await self._mqtt_proxy.publish_state_changes()  # TODO as task

                # Push MQTT commands => devices
                self._mqtt_proxy.process_commands()

                # Push device commands => Hue
                await self._hue_bridge.send_device_commands()  # TODO as task

                await asyncio.sleep(0.05)

        finally:
            await self._mqtt_proxy.publish_last_wills()

    async def _wait_for_mqtt_connection(self):
        timeout = self.CONNECTION_TIMEOUT
        try:
            return await asyncio.wait_for(self._mqtt_proxy.connect(), timeout)
        except asyncio.exceptions.TimeoutError:
            raise asyncio.exceptions.TimeoutError(f"couldn't connect to MQTT (within {timeout}s)!") from None

    async def _wait_for_hue_connection(self):
        timeout = self.CONNECTION_TIMEOUT
        try:
            return await asyncio.wait_for(self._hue_bridge.connect(), timeout)
        except asyncio.exceptions.TimeoutError:
            raise asyncio.exceptions.TimeoutError(f"couldn't connect to Hue bridge (within {timeout}s)!") from None
