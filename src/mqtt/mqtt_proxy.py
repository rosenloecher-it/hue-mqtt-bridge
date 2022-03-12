import asyncio
import json
import logging
from collections import deque
from typing import Dict, List, Optional, Deque

from paho.mqtt.client import MQTTMessage

from src.thing.thing import Thing, StateMessage
from src.mqtt.mqtt_client import MqttClient

_logger = logging.getLogger(__name__)


class MqttProxy:

    def __init__(self, mqtt_client: Optional[MqttClient], things: List[Thing]):

        self._mqtt_client = mqtt_client
        self._things = things

        self._state_messages: Deque[StateMessage] = deque()

        self._command_subscriptions: Dict[str, List[Thing]] = {}
        for thing in self._things:
            subscriptions = thing.mqtt_subscriptions
            for subscription in subscriptions:
                listeners = self._command_subscriptions.get(subscription)
                if not listeners:
                    listeners = []
                    self._command_subscriptions[subscription] = listeners
                listeners.append(thing)

    async def close(self):
        await self.publish_state_messages()  # contains the last wills
        self._mqtt_client = None  # used as shutdown marker

    async def connect(self):
        if self._mqtt_client:
            self._mqtt_client.connect()

            while True:
                if self._mqtt_client.is_connected():
                    topics = list(self._command_subscriptions.keys())
                    self._mqtt_client.subscribe(topics)
                    _logger.info("connected + subscribed")
                    break

                await asyncio.sleep(0.005)

    def is_connected(self):
        if self._mqtt_client:
            return self._mqtt_client.is_connected()
        else:
            return False

    def fetch_state_changes(self) -> bool:
        for thing in self._things:
            state_message = thing.get_state_messages()
            if state_message:
                self._state_messages.extend(state_message)

        return bool(self._state_messages)

    async def publish_state_messages(self):
        while self._state_messages:
            m = self._state_messages.popleft()
            payload = m.payload
            if isinstance(payload, dict):
                payload = json.dumps(payload, sort_keys=True)
            self._mqtt_client.publish(topic=m.topic, payload=payload, retain=m.retain)

    async def process_timer(self):
        """placeholder for reconnects"""

    async def publish_last_wills(self):
        for thing in self._things:
            thing.close()

        self.fetch_state_changes()
        await self.publish_state_messages()

    @classmethod
    def ensure_string(cls, value_in) -> str:
        if isinstance(value_in, bytes):
            return value_in.decode("utf-8")

    def process_thing_commands(self):
        """dispatch incoming MQTT command to devices"""
        if not self._mqtt_client:
            return

        messages: List[MQTTMessage] = self._mqtt_client.get_messages()
        for message in messages:
            topic = message.topic
            listeners: List[Thing] = self._command_subscriptions.get(topic)
            if listeners:
                payload = self.ensure_string(message.payload)
                for listener in listeners:
                    listener.process_mqtt_command(topic, payload)
