import asyncio
import datetime
import logging
import random
import signal
import threading
from asyncio import Task
from typing import Callable, Optional

from src.hue.hue_connector import HueConnector
from src.mqtt.mqtt_proxy import MqttProxy
from src.time_utils import TimeUtils

_logger = logging.getLogger(__name__)


class Runner:

    PROCESSING_TIMEOUT = 10  # seconds

    def __init__(self, hue_bridge: HueConnector, mqtt_proxy: MqttProxy):

        self._hue_bridge = hue_bridge
        self._mqtt_proxy = mqtt_proxy

        self._shutdown = False

        self._hue_task = None  # type: Optional[Task]
        self._mqtt_task = None  # type: Optional[Task]

        self._hue_next_timer_start = self.get_next_timer_start()
        self._mqtt_next_timer_start = self.get_next_timer_start()

        if threading.current_thread() is threading.main_thread():
            # integration tests may run the service in a thread...
            signal.signal(signal.SIGINT, self._signal_shutdown)
            signal.signal(signal.SIGTERM, self._signal_shutdown)

    def _signal_shutdown(self, sig, _frame):
        _logger.info("shutdown signaled (%s)", sig)
        self._shutdown = True

    async def run(self):
        """endless loop"""

        await self._process_with_timeout(self._mqtt_proxy.connect(), "couldn't connect to MQTT")
        await self._process_with_timeout(self._hue_bridge.connect(), "couldn't connect to Hue bridge")

        try:
            while not self._shutdown:

                if self._mqtt_task:
                    self._mqtt_task = self._check_or_finish_task(self._mqtt_task)
                if not self._mqtt_task:
                    if self._mqtt_proxy.fetch_state_changes():
                        self._mqtt_task = self._create_task(self._mqtt_proxy.publish_state_messages)
                    else:
                        if TimeUtils.now() > self._mqtt_next_timer_start:
                            self._mqtt_next_timer_start = self.get_next_timer_start()
                            self._mqtt_task = self._create_task(self._mqtt_proxy.process_timer)

                # Push MQTT commands => devices
                self._mqtt_proxy.process_thing_commands()

                if self._hue_task:
                    self._hue_task = self._check_or_finish_task(self._hue_task)
                if not self._hue_task:
                    if self._hue_bridge.fetch_commands():
                        self._hue_task = self._create_task(self._hue_bridge.send_commands)
                    else:
                        if TimeUtils.now() > self._hue_next_timer_start:
                            self._hue_next_timer_start = self.get_next_timer_start()
                            self._hue_task = self._create_task(self._hue_bridge.process_timer)

                await asyncio.sleep(0.05)

        finally:
            await self._mqtt_proxy.publish_last_wills()

    @classmethod
    def _check_or_finish_task(cls, task: Task) -> Task:
        if task.done():
            task.result()  # may raise exception from task
            task.cancel()
            task = None
        return task

    def _create_task(self, func_declaration: Callable, timeout: float = None) -> Task:
        func_name = f"{func_declaration.__name__} failure"
        return asyncio.create_task(self._process_with_timeout(func_declaration(), func_name, timeout))

    @classmethod
    async def _process_with_timeout(cls, func_instance: Callable, error_info: Optional[str] = None, timeout: float = None):
        timeout = timeout or cls.PROCESSING_TIMEOUT
        try:
            return await asyncio.wait_for(func_instance, timeout)
        except asyncio.exceptions.TimeoutError:
            raise asyncio.exceptions.TimeoutError("{0} (timeout {1:.1f}s) - abort!".format(error_info, timeout)) from None

    @classmethod
    def get_next_timer_start(cls) -> datetime.datetime:
        return TimeUtils.now() + datetime.timedelta(seconds=60 + random.randint(-3, 3))
