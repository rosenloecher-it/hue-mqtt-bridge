from __future__ import annotations

import copy
from typing import List, Optional
from unittest.mock import MagicMock

from aiohue.v2 import EventType
from aiohue.v2.models.feature import OnFeature
from aiohue.v2.models.light import Light

from src.hue.hue_config import HueBridgeConfKey
from src.hue.hue_connector import HueConnector
from src.thing.thing import Thing, StateMessage
from src.utils.time_utils import TimeUtils
from test.hue.hue_bridge_simu import HueBridgeSimu


class HueConnectorSimu(HueConnector):

    def __init__(self, things: Optional[List[Thing]] = None):
        config = {
            HueBridgeConfKey.HOST: "dummy_host",
            HueBridgeConfKey.APP_KEY: "dummy_app_key",

            # shorter time will blow the tests, because an intermediate group update wil be sent!
            HueBridgeConfKey.GROUP_DEBOUNCE_TIME: 20,  # milliseconds
        }
        if things is None:
            things = HueBridgeSimu.configurable_things()
            for thing in things:
                thing._state_debounce_time = 0.02  # seconds

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

    async def simu_on_state_changed(self, device_key: str, on_state: bool):
        hue_item = copy.deepcopy(self._hue_items.get(device_key))
        if hue_item and hasattr(hue_item, "on") and isinstance(hue_item.on, OnFeature):
            hue_item.on = OnFeature(on_state)
        else:
            raise Exception("Wrong test setup")

        self._on_state_changed(EventType.RESOURCE_UPDATED, hue_item)

        await TimeUtils.sleep(0.1)

    def prepare_on_state(self, device_key: str, on_state: bool):
        hue_item = self._hue_items.get(device_key)
        if hue_item and hasattr(hue_item, "on") and isinstance(hue_item.on, OnFeature):
            hue_item.on = OnFeature(on_state)
        else:
            raise Exception("Wrong test setup")

    def prepare_dim_state(self, device_key: str, brightness: float):
        hue_item = self._hue_items.get(device_key)

        if not hue_item.dimming:
            raise RuntimeError("Wrong test setup: Dimming not supported!")
        if hue_item.dimming.min_dim_level is not None and brightness < hue_item.dimming.min_dim_level:
            raise RuntimeError("Wrong test setup: 'brightness' not adapted!")
        hue_item.dimming.brightness = brightness

    async def simu_command(self, device_key: str, command: str):
        thing = self._things[device_key]
        # noinspection PyProtectedMember
        thing.process_mqtt_command(thing._cmd_topic, command)

        self.fetch_commands()

        await self.send_commands()

    async def _set_light(self, hue_item: Light, on: Optional[bool], brightness: Optional[float]):
        self.set_light(id=hue_item.id, on=on, brightness=brightness)

    @classmethod
    async def create(cls, watch_initial_messages=False) -> HueConnectorSimu:
        connector = HueConnectorSimu()
        await connector.connect()

        await TimeUtils.sleep(0.1)  # wait until all debounce group observers have fired

        if not watch_initial_messages:
            connector.reset_actions()

        return connector
