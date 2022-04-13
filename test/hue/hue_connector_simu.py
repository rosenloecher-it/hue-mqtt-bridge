from __future__ import annotations

import copy
from typing import List, Optional
from unittest.mock import MagicMock

from aiohue.v2 import EventType
from aiohue.v2.models.light import Light

from src.hue.hue_command import HueCommand, HueCommandType, SwitchType
from src.hue.hue_config import HueBridgeConfKey
from src.hue.hue_connector import HueConnector
from src.thing.thing import Thing, StateMessage
from src.utils.time_utils import TimeUtils
from test.hue.hue_bridge_simu import HueBridgeSimu, RoomSimu


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

    async def simu_command(self, device_key: str, command: str):
        thing = self._things[device_key]
        # noinspection PyProtectedMember
        thing.process_mqtt_command(thing._cmd_topic, command)

        self.fetch_commands()

        await self.send_commands()

        try:
            hue_command = HueCommand.parse(command)
        except ValueError:
            hue_command = None  # let invalid command through

        thing = self._things.get(device_key)
        if hue_command and isinstance(thing, RoomSimu):
            # simu change group light: normally the bridge would do that
            updated_group_light = self._hue_items.get(thing.hue_grouped_light.id)  # use the updated instance!
            updated_group_light = copy.deepcopy(updated_group_light)

            if hue_command.type == HueCommandType.SWITCH:
                if hue_command.switch == SwitchType.ON:
                    updated_group_light.on.on = True
                elif hue_command.switch == SwitchType.OFF:
                    updated_group_light.on.on = False
                elif hue_command.switch == SwitchType.TOGGLE:
                    updated_group_light.on.on = not updated_group_light.on.on
                else:
                    raise ValueError("?")
                self._on_state_changed(EventType.RESOURCE_UPDATED, updated_group_light)
            elif hue_command.type == HueCommandType.DIM:
                new_on = True if hue_command.dim >= thing.min_brightness else False
                if new_on != updated_group_light.on.on:
                    updated_group_light.on.on = new_on
                    self._on_state_changed(EventType.RESOURCE_UPDATED, updated_group_light)

        await TimeUtils.sleep(0.1)

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

        await TimeUtils.sleep(0.1)  # wait until all debounce group observers have fired

        if not watch_initial_messages:
            connector.reset_actions()

        return connector
