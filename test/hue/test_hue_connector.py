from __future__ import annotations

import copy
from typing import List, Optional
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock, call

from aiohue.v2 import EventType
from aiohue.v2.models.light import Light

from src.thing.thing import Thing, StateMessage
from src.hue.hue_command import HueCommand, HueCommandType, SwitchType
from src.hue.hue_config import HueBridgeConfKey
from src.hue.hue_connector import HueConnector
from test.hue.hue_bridge_simu import HueBridgeSimu, RoomSimu


# noinspection PyProtectedMember
class HueConnectorSimu(HueConnector):

    def __init__(self, things: Optional[List[Thing]] = None):
        config = {
            HueBridgeConfKey.HOST: "dummy_host",
            HueBridgeConfKey.APP_KEY: "dummy_app_key",
        }
        if things is None:
            things = HueBridgeSimu.configurable_things()

        super().__init__(config, things)

        self.set_light = None

        self.reset_actions()

    def reset_actions(self):
        self.set_light = MagicMock("set_light")

        for device in self._things.values():
            device.get_state_messages()  # messages gets removed too

    def get_state_message(self, remove_timestamps=True) -> List[StateMessage]:
        state_messages = []
        for thing in self._things.values():
            messages = thing.get_state_messages()
            if messages:
                for message in messages:
                    if remove_timestamps:
                        del message.payload["timestamp"]
                    state_messages.append(message)
        return state_messages

    async def _initialize_hue_bridge(self):
        self._bridge = HueBridgeSimu.create_hue_bridge()

    async def simu_command(self, device_key: str, command: str):
        thing = self._things[device_key]
        thing.process_mqtt_command(thing._cmd_topic, command)

        result = self.fetch_commands()
        assert result  # must be fetched

        await self.send_commands()

        thing = self._things.get(device_key)
        if isinstance(thing, RoomSimu):
            hue_command = HueCommand.parse(command)
            if hue_command.type == HueCommandType.SWITCH:
                # simu changed group light
                updated_group_light = copy.deepcopy(thing.hue_grouped_light)
                if hue_command.switch == SwitchType.ON:
                    updated_group_light.on.on = True
                elif hue_command.switch == SwitchType.OFF:
                    updated_group_light.on.on = False
                elif hue_command.switch == SwitchType.TOGGLE:
                    updated_group_light.on.on = not updated_group_light.on.on
                else:
                    raise ValueError("?")
                self._on_state_changed(EventType.RESOURCE_UPDATED, updated_group_light)

    async def _set_light(self, hue_item: Light, on: Optional[bool], brightness: Optional[float]):
        self.set_light(id=hue_item.id, on=on, brightness=brightness)

        if on is None and brightness is None:
            raise RuntimeError("Missing action (_set_light)!")

        update = copy.deepcopy(hue_item)
        if on is not None:
            update.on.on = bool(on)
        if brightness is not None:
            if not update.dimming:
                raise RuntimeError("Dimming not supported!")
            if update.dimming.min_dim_level is not None and brightness < update.dimming.min_dim_level:
                raise RuntimeError("'brightness' not adapted!")
            update.dimming.brightness = brightness

        self._on_state_changed(EventType.RESOURCE_UPDATED, update)

    @classmethod
    async def create(cls, watch_initial_messages=False) -> HueConnectorSimu:
        connector = HueConnectorSimu()
        await connector.connect()

        if not watch_initial_messages:
            connector.reset_actions()

        return connector


class TestHueConnector(IsolatedAsyncioTestCase):

    @classmethod
    def state_message(cls, hue_id: str, status: str, hue_type="light", brightness=100):
        """generate an expected state message"""
        return StateMessage(
            topic=hue_id + "/state",
            payload={
                "brightness": brightness,
                "id": hue_id,
                "name": hue_id,
                "status": status,
                "type": hue_type,
            },
            retain=HueBridgeSimu.DEFAULT_RETAIN,
        )

    async def test_on_off(self):
        connector = await HueConnectorSimu.create()

        await connector.simu_command(HueBridgeSimu.ID_GROUP, "on")

        calls = [
            call(id=HueBridgeSimu.ID_COLOR1, on=True, brightness=None),
            call(id=HueBridgeSimu.ID_COLOR2, on=True, brightness=None),
        ]
        connector.set_light.assert_has_calls(calls)

        expected_messages = [
            self.state_message(HueBridgeSimu.ID_COLOR1, "on"),
            self.state_message(HueBridgeSimu.ID_COLOR2, "on"),
            self.state_message(HueBridgeSimu.ID_GROUP, "on", hue_type="group"),
        ]
        result_messages = connector.get_state_message()
        self.assertCountEqual(result_messages, expected_messages)

        connector.reset_actions()
        await connector.simu_command(HueBridgeSimu.ID_GROUP, " oFF ")
        calls = [
            call(id=HueBridgeSimu.ID_COLOR1, on=False, brightness=None),
            call(id=HueBridgeSimu.ID_COLOR2, on=False, brightness=None),
        ]
        connector.set_light.assert_has_calls(calls)

        expected_messages = [
            self.state_message(HueBridgeSimu.ID_COLOR1, "off", brightness=0),
            self.state_message(HueBridgeSimu.ID_COLOR2, "off", brightness=0),
            self.state_message(HueBridgeSimu.ID_GROUP, "off", hue_type="group", brightness=0),
        ]
        result_messages = connector.get_state_message()
        self.assertCountEqual(result_messages, expected_messages)

    async def test_dim(self):
        connector = await HueConnectorSimu.create()

        await connector.simu_command(HueBridgeSimu.ID_GROUP, "69")

        calls = [
            call(id=HueBridgeSimu.ID_COLOR1, on=True, brightness=69),
            call(id=HueBridgeSimu.ID_COLOR2, on=True, brightness=69),
        ]
        connector.set_light.assert_has_calls(calls)

        expected_messages = [
            self.state_message(HueBridgeSimu.ID_COLOR1, "on", brightness=69),
            self.state_message(HueBridgeSimu.ID_COLOR2, "on", brightness=69),
            # missing group call
        ]
        result_messages = connector.get_state_message()
        self.assertCountEqual(result_messages, expected_messages)

        connector.reset_actions()
        await connector.simu_command(HueBridgeSimu.ID_GROUP, " oFF ")
        calls = [
            call(id=HueBridgeSimu.ID_COLOR1, on=False, brightness=None),
            call(id=HueBridgeSimu.ID_COLOR2, on=False, brightness=None),
        ]
        connector.set_light.assert_has_calls(calls)

        expected_messages = [
            self.state_message(HueBridgeSimu.ID_COLOR1, "off", brightness=0),
            self.state_message(HueBridgeSimu.ID_COLOR2, "off", brightness=0),
            self.state_message(HueBridgeSimu.ID_GROUP, "off", hue_type="group", brightness=0),
        ]
        result_messages = connector.get_state_message()
        self.assertCountEqual(result_messages, expected_messages)
