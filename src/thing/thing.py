import logging
from logging import Logger
from typing import Dict, List, Union, Optional

import attr

from src.thing.thing_config import ThingDefaults
from src.thing.thing_event import ThingEvent
from src.hue.hue_command import HueCommand


@attr.frozen
class StateMessage:

    topic: str
    payload: Union[str, Dict[str, any]]
    retain: bool


class Thing:

    def __init__(self, hue_id: str, name: str, cmd_topic: str, state_topic: str, last_will: str, retain: bool,
                 min_brightness: float, state_debounce_time: float = ThingDefaults.STATE_DEBOUNCE_TIME):
        self._name = name
        self._hue_id = hue_id
        self._cmd_topic = cmd_topic
        self._state_topic = state_topic
        self._last_will = last_will
        self._retain = retain
        self._min_brightness = min_brightness
        self._state_debounce_time = state_debounce_time

        self.__logger: Optional[Logger] = None

        self._messages: List[StateMessage] = None
        self._hue_command: Optional[HueCommand] = None

        self._closed = False

    def __str__(self):
        return f"id: {self.hue_id}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.hue_id})"

    def close(self):
        if not self._closed:
            if self._last_will:
                self._add_state_message(StateMessage(topic=self._state_topic, payload=self._last_will, retain=self._retain))

            self._closed = True

    def _add_state_message(self, message: StateMessage):
        if self._messages is None:
            self._messages = []
        self._messages.append(message)

    @property
    def hue_id(self) -> str:
        return self._hue_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def cmd_topic(self) -> str:
        return self._cmd_topic

    @property
    def state_topic(self) -> str:
        return self._state_topic

    @property
    def last_will(self) -> str:
        return self._last_will

    @property
    def retain(self) -> bool:
        return self._retain

    @property
    def min_brightness(self) -> float:
        return self._min_brightness

    @property
    def state_debounce_time(self) -> float:
        return self._state_debounce_time

    @property
    def _logger(self):
        if self.__logger is None:
            log_name = self._name or "???"
            log_name = f"{self.__class__.__name__}({log_name})"
            self.__logger = logging.getLogger(log_name)
        return self.__logger

    @property
    def mqtt_subscriptions(self) -> List[str]:
        """return MQTT topics the thing is listen to"""
        return [self._cmd_topic] if self._cmd_topic else []

    def get_state_messages(self) -> Optional[List[StateMessage]]:
        if not self._messages:
            return None
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

    def process_state_change(self, event: ThingEvent):
        if self._closed:
            return

        self._add_state_message(StateMessage(
            topic=self._state_topic,
            payload=event.to_data(),
            retain=self._retain
        ))
