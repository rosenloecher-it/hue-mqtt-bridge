import logging
import typing
from collections import OrderedDict
from typing import Dict, Union

import attr
from aiohue.discovery import discover_nupnp
from aiohue.v2 import DevicesController, LightsController, GroupsController
from aiohue.v2.models.room import Room

from src.hue.hue_connector import HueConnectorBase
from src.thing.thing import Thing

_logger = logging.getLogger(__name__)


@attr.define
class HueItem:
    item: Union[DevicesController, GroupsController, LightsController] = None
    name: str = None
    type: str = None


@attr.define
class HueCache:
    devices: Dict[str, DevicesController] = None
    rooms: typing.OrderedDict[str, Room] = None
    lights: typing.OrderedDict[str, LightsController] = None


class HueExplorer(HueConnectorBase):

    @classmethod
    async def discover(cls):
        _logger.debug("discover")
        print("\nDiscovering Hue bridges...\n")

        bridges = await discover_nupnp()
        if bridges:
            for bridge in bridges:
                support_info = "" if bridge.supports_v2 else " Bridge is NOT supported (not V2)!"
                print(f"Found bridge: IP {bridge.host} (ID {bridge.id}){support_info}")
        else:
            print("No bridge found.")

        print()

    def _cached_hue_items(self) -> HueCache:
        cache = HueCache()

        cache.devices = {}
        for d in self._bridge.devices:
            item = HueItem(item=d, name=d.metadata.name, type="DEVICE")
            cache.devices[d.id] = item

        rooms = []
        for g in self._bridge.groups:
            if isinstance(g, Room):
                rooms.append(HueItem(item=g, name=g.metadata.name, type=g.type.name))
        rooms = sorted(rooms, key=lambda r: r.name.lower())
        cache.rooms = OrderedDict({r.item.id: r for r in rooms})

        lights = []
        for light in self._bridge.lights:
            lights.append(HueItem(item=light, name=light.metadata.name, type=light.type.name))
        lights = sorted(lights, key=lambda l: l.name.lower())
        cache.lights = OrderedDict({c.item.id: c for c in lights})

        return cache

    @classmethod
    def get_offset(cls, level: int):
        return "    " * level

    def _print_bridge(self):
        self.print()
        self.print("HUE BRIDGE")
        offset = self.get_offset(1)
        self.print(f"{offset}HOST:        {self._host}")
        self.print(f"{offset}NAME:        {self._bridge.config.name}")
        self.print(f"{offset}ID:          {self._bridge.bridge_id}")
        self.print(f"{offset}MODEL:       {self._bridge.config.model_id}")
        self.print(f"{offset}API VERSION: {self._bridge.config.software_version}")

    def print_rooms(self, hue_cache: HueCache):
        self.print()
        self.print("HUE ROOMS (WITH ASSIGNED LIGHTS)")
        for room in hue_cache.rooms.values():
            offset = self.get_offset(1)
            self.print(f"{offset}{room.type} {room.name} ({room.item.id})")

            offset = self.get_offset(2)
            lights = []
            for child_resource in room.item.children:
                device_item = hue_cache.devices.get(child_resource.rid)
                if device_item is not None:
                    for light_id in device_item.item.lights:
                        light = hue_cache.lights.get(light_id)
                        lights.append(light)
                else:
                    light_item = hue_cache.lights.get(child_resource.rid)
                    if light_item:
                        lights.append(light_item)
            lights = sorted(lights, key=lambda l: l.name.lower())
            for light in lights:
                self.print(f"{offset}LIGHT {light.name} ({light.item.id})")

    def print_lights(self, hue_cache: HueCache):

        def supports(value: bool) -> str:
            return "[" + ("X" if value else " ") + "]"

        self.print()
        self.print("LIGHTS")
        for light in hue_cache.lights.values():
            offset = self.get_offset(1)
            self.print(f"{offset}LIGHT {light.name} ({light.item.id})")

            dimming_info = ""
            if light.item.dimming:
                if light.item.dimming.min_dim_level is None:
                    dimming_info = " (No minimum dimming value!?)"
                else:
                    dimming_info = f" (MIN: {round(light.item.dimming.min_dim_level)}%)" if light.item.supports_dimming else ""

            offset = self.get_offset(2)
            self.print(f"{offset}COLOR TEMPERATURE: {supports(light.item.color_temperature)}")
            self.print(f"{offset}COLOR:             {supports(light.item.supports_color)}")
            self.print(f"{offset}DIMMING:           {supports(light.item.supports_dimming)}{dimming_info}")

    def _print_config(self, hue_cache: HueCache):
        self.print()
        self.print("CONFIGURED THINGS")

        things = sorted(self._things.values(), key=lambda d: d.name.lower())

        for thing in things:
            offset = self.get_offset(1)
            self.print(f"{offset}CONFIGURED THING: {thing.name}")

            offset = self.get_offset(2)
            hue_item = hue_cache.rooms.get(thing.hue_id) or hue_cache.lights.get(thing.hue_id)
            if hue_item:
                self.print(f"{offset}HUE ITEM:      {hue_item.type} {hue_item.name} ({hue_item.item.id})")
            else:
                self.print(f"{offset}HUE ITEM:      NOT FOUND !?")
            self.print(f"{offset}COMMAND TOPIC: {thing.cmd_topic}")
            self.print(f"{offset}STATE TOPIC:   {thing.state_topic}")
            self.print(f"{offset}RETAIN:        [" + ("X" if thing.retain else " ") + "]")
            self.print(f"{offset}LAST WILL:     {thing.last_will}")

            thing_event = self._generate_thing_status(hue_item.item)
            message = Thing.event_to_message(thing_event)
            self.print(f"{offset}CURRENT STATE: {message}")

    async def run_tools(self):
        if not self._bridge:
            await self.connect()

        hue_cache = self._cached_hue_items()

        self._print_bridge()
        self.print_lights(hue_cache)
        self.print_rooms(hue_cache)
        self._print_config(hue_cache)
        self.print()

    # noinspection PyMethodMayBeStatic
    def print(self, text=""):
        print(text)
