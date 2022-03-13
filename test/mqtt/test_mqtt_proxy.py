from typing import List
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock, call

from paho.mqtt.client import MQTTMessage

from src.hue.hue_command import HueCommandType
from src.mqtt.mqtt_client import MqttClient
from src.mqtt.mqtt_proxy import MqttProxy
from src.thing.thing import Thing, StateMessage


class TestMqttProxy(IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.things = []
        for i in range(2):
            key = f"{i}"
            self.things.append(
                Thing(
                    hue_id=key, name=key, cmd_topic=key + "/cmd", state_topic=key + "/state",
                    last_will="last_will_" + key, retain=(i == 1), min_brightness=10 * i
                )
            )
        self.client = MagicMock(MqttClient, autospec=True)
        self.proxy = MqttProxy(self.client, self.things)

    async def asyncTearDown(self):
        await self.proxy.close()

    async def test_full_roundtrip(self):
        # check connect + subscribe
        await self.proxy.connect()
        self.client.connect.assert_called()
        self.client.subscribe.assert_called_with(['0/cmd', '1/cmd'])

        # check publish state messages
        expected_messages = []
        for t in self.things:
            for i in range(2):
                message = StateMessage(topic=t.state_topic, payload=f"payload-{t.hue_id}-{i}", retain=t.retain)

                # TODO process_state_change
                t._add_state_message(message)
                expected_messages.append(message)

        self.proxy.fetch_state_changes()
        await self.proxy.publish_state_messages()

        calls = []
        for m in expected_messages:
            calls.append(call(topic=m.topic, payload=m.payload, retain=m.retain))
        self.client.publish.assert_has_calls(calls)

        # check commands
        mqtt_messages: List[MQTTMessage] = []
        for t in self.things:
            m = MQTTMessage(topic=t.cmd_topic.encode())
            m.payload = f"9{t.hue_id}".encode()
            mqtt_messages.append(m)

        self.client.get_messages.return_value = mqtt_messages

        for t in self.things:
            self.assertEqual(t._hue_command, None)
        self.proxy.process_thing_commands()
        for t in self.things:
            hue_command = t.get_hue_command()
            self.assertEqual(hue_command.type, HueCommandType.DIM)
            self.assertEqual(hue_command.dim, float(f"9{t.hue_id}"))

        # close + last wills
        self.client.publish = MagicMock("publish")  # reset mock
        calls = []
        for t in self.things:
            calls.append(call(topic=t.state_topic, payload=t.last_will, retain=t.retain))
            t.close()

        await self.proxy.close()

        self.client.publish.assert_has_calls(calls)
