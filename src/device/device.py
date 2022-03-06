import logging
from logging import Logger
from typing import Dict, List, Union, Optional

import attr

from src.device.device_event import DeviceEvent
from src.hue.hue_command import HueCommand
from src.time_utils import TimeUtils


@attr.frozen
class DeviceMessage:

    topic: str
    payload: Union[str, Dict[str, any]]
    retain: bool


class Device:

    def __init__(self, hue_id: str, name: str, cmd_topic: str, state_topic: str, last_will: str, retain: bool):
        self._name = name
        self._hue_id = hue_id
        self._cmd_topic = cmd_topic
        self._state_topic = state_topic
        self._last_will = last_will
        self._retain = retain

        self.__logger = None  # type: Optional[Logger]

        self._messages: List[DeviceMessage] = []
        self._hue_command: Optional[HueCommand] = None

        self._closed = False

    def close(self):
        if not self._closed:
            if self._last_will:
                self._messages.append(DeviceMessage(
                    topic=self._state_topic,
                    payload=self._last_will,
                    retain=self._retain
                ))

            self._closed = True

    @property
    def hue_id(self) -> str:
        return self._hue_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def _logger(self):
        if self.__logger is None:
            log_name = self._name or "???"
            log_name = f"{self.__class__.__name__}({log_name})"
            self.__logger = logging.getLogger(log_name)
        return self.__logger

    @property
    def mqtt_subscriptions(self) -> List[str]:
        """return MQTT topics the device is listen to"""
        return [self._cmd_topic] if self._cmd_topic else []

    def get_mqtt_messages(self) -> List[DeviceMessage]:
        if not self._messages:
            return []
        messages = self._messages
        self._messages = []
        return messages

    def process_mqtt_command(self, _topic: str, payload: str):
        if self._closed:
            return

        try:
            new_command = HueCommand.parse(payload)
            if self._hue_command:
                self._logger.warning("Overwrite queued command (%s) with new one (%s)", self._hue_command, new_command)
            # else:
            #     self._logger.debug("process_mqtt_command: %s => %s", payload, new_command)
            self._hue_command = new_command

        except ValueError as ex:
            self._logger.warning(ex)

    def get_hue_command(self) -> Optional[HueCommand]:
        try:
            return self._hue_command
        finally:
            self._hue_command = None

    @classmethod
    def event_to_message(cls, event: DeviceEvent) -> Dict[str, any]:
        # noinspection PyDataclass
        data = attr.asdict(event)

        for key in list(data.keys()):
            if data[key] is None:
                del data[key]

        status = data.get("status")
        if not data.get("status"):
            data["status"] = "error"
        else:
            data["status"] = status.value

        brightness = data.get("brightness")
        if brightness is not None:
            data["brightness"] = int(round(brightness))

        data["timestamp"] = TimeUtils.now(no_ms=True).isoformat()

        return data

    def process_state_change(self, event: DeviceEvent):
        if self._closed:
            return

        # self._logger.debug("process_state_change: %s", event)
        payload = self.event_to_message(event)

        self._messages.append(DeviceMessage(
            topic=self._state_topic,
            payload=payload,
            retain=self._retain
        ))
