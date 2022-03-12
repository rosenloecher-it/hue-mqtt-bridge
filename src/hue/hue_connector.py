import datetime
import logging
from collections import deque
from typing import Optional, List, Dict, Set, Union, Deque

import aiohue
import attr
from aiohue import HueBridgeV2
from aiohue.v2 import EventType
from aiohue.v2.models.feature import OnFeature
from aiohue.v2.models.grouped_light import GroupedLight
from aiohue.v2.models.light import Light
from aiohue.v2.models.room import Room

from src.app_config import ConfigException
from src.device.device import Device
from src.hue.hue_command import HueCommand, HueCommandType, SwitchType
from src.hue.hue_config import HueBridgeConfKey
from src.hue.hue_event_converter import HueEventConverter
from src.time_utils import TimeUtils

_logger = logging.getLogger(__name__)


class HueException(Exception):
    pass


@attr.frozen
class StateChange:

    event_type: any
    item: any


class HueConnectorBase:

    def __init__(self, config, devices: List[Device]):

        self._host = config[HueBridgeConfKey.HOST]
        self._app_key = config[HueBridgeConfKey.APP_KEY]
        self._devices: Dict[str, Device] = {}

        self._bridge: Optional[HueBridgeV2] = None

        for device in devices:
            self._devices[device.hue_id] = device

    async def connect(self):
        await self._initialize_hue_bridge()

    async def _initialize_hue_bridge(self):
        if self._bridge:
            await self.close()

        try:
            self._bridge = HueBridgeV2(self._host, self._app_key)
        except aiohue.errors.Unauthorized:
            raise ConfigException("Hue bridge rejected the app token. Do you have to create an app token first (--create-app-key)?")

        await self._bridge.initialize()

    async def close(self):
        if self._bridge:
            await self._bridge.close()
            self._bridge = None

    async def run_tools(self):
        """put main functionality here"""
        # do nothing in base implemation!


class HueConnector(HueConnectorBase):

    def __init__(self, config, devices: List[Device]):
        super().__init__(config, devices)

        self._device_commands: Deque[(Device, HueCommand)] = deque()

        self._cached_group_children: Dict[str, List[str]] = {}
        self._cached_grouped_light_ids_to_groups: Dict[str, str] = {}
        self._cached_hue_items: Dict[str, Union[Light, GroupedLight]] = {}

        self._next_refresh_time = self.get_next_refresh_time()

    async def connect(self):
        self._initialize_hue_bridge()

        self._rebuild_caches()
        self._next_refresh_time = self.get_next_refresh_time()

    def _initialize_hue_bridge(self):
        super()._initialize_hue_bridge()

        self._bridge.subscribe(self._on_state_changed)

    def _rebuild_caches(self):
        self._cached_group_children = {}
        self._cached_grouped_light_ids_to_groups = {}
        self._cached_hue_items = {}

        for hue_light in self._bridge.lights:
            self._on_state_changed(EventType.RESOURCE_UPDATED, hue_light)

        for hue_group in self._bridge.groups:
            device = self._devices.get(hue_group.id)
            if device:
                if isinstance(hue_group, Room):  # Zone is inherited from Room
                    self._cached_grouped_light_ids_to_groups[hue_group.grouped_light] = hue_group.id

                    hue_children_ids = self._find_lights_for_group(hue_group)
                    self._cached_group_children[hue_group.id] = hue_children_ids
                else:
                    _logger.warning("Only 'Rooms/Zones' are supported as groups. '%s' is of type '%s'. It's ignored!", type(hue_group))
                    del self._devices[hue_group.id]
                    continue

        for hue_group in self._bridge.groups:
            self._on_state_changed(EventType.RESOURCE_UPDATED, hue_group)

        not_found_items = []
        for device in self._devices.values():
            if not self._cached_hue_items.get(device.hue_id):
                not_found_items.append(device.name)
                # TODO publish offline
        if not_found_items:
            _logger.warning("Unknown hue items found (%s)!", ", ".join(not_found_items))

    async def close(self):
        await super().close()

        self._cached_hue_items = {}

    def _on_state_changed(self, event_type: EventType, item):
        if not item and not item.id:
            return

        self._cached_hue_items[item.id] = item

        if isinstance(item, Room):
            return

        # rooms (from grouped light) only
        room_item = None
        device = self._devices.get(item.id)
        if not device and isinstance(item, GroupedLight):
            room_item_id = self._cached_grouped_light_ids_to_groups.get(item.id)
            room_item = self._cached_hue_items.get(room_item_id)
            if room_item:
                device = self._devices.get(room_item.id)

        if not device:
            return

        device_event = HueEventConverter.to_device_event(event_type, item, device.name)
        if room_item is not None:
            device_event.id = device.hue_id
            device_event.name = device.name
            device_event.brightness = self._get_average_brightness_for_group(room_item)

        # _logger.debug("_on_state_changed: %s, %s => %s", event_type, item, device_event)
        device.process_state_change(device_event)

    async def process_timer(self):
        """placeholder for reconnects or other organisational stuff"""
        if self._bridge and TimeUtils.now() > self._next_refresh_time:
            self._next_refresh_time = self.get_next_refresh_time()
            _logger.info("full refresh")
            await self._bridge.fetch_full_state()
            self._rebuild_caches()

    def _get_average_brightness_for_group(self, hue_group: Room) -> Optional[float]:
        hue_children = self._get_lights_for_group(hue_group)

        dimming_count = 0
        brightness_count = 0
        brightness_sum = 0

        for hue_child in hue_children:
            if isinstance(hue_child, Light):
                brightness_count += 1
                is_on = hue_child.on.on
                if hue_child.dimming:
                    dimming_count += 1
                    brightness_sum += hue_child.dimming.brightness if is_on else 0
                else:
                    brightness_sum += 100.0 if is_on else 0

        if dimming_count == 0:
            return None

        average = brightness_sum / brightness_count
        return average

    def _get_lights_for_group(self, hue_group: Room) -> List[Light]:
        hue_children_ids = self._cached_group_children.get(hue_group.id)
        hue_children = []
        for hue_child_id in hue_children_ids:
            hue_child = self._cached_hue_items.get(hue_child_id)
            if hue_child:
                hue_children.append(hue_child)

        return hue_children

    def _find_lights_for_group(self, hue_group: Room) -> List[str]:
        """find all light ids for a group"""
        device_children: Dict[str, Set[str]] = {}
        cached_lights: Dict[str, Light] = {}

        for hue_device in self._bridge.devices:
            device_children[hue_device.id] = hue_device.lights
        for hue_light in self._bridge.lights:
            cached_lights[hue_light.id] = hue_light

        hue_children_ids = []

        if isinstance(hue_group, Room):
            for child_resource in hue_group.children:
                child_light_ids = list(device_children.get(child_resource.rid, set()))
                for child_light_id in child_light_ids:
                    hue_child = cached_lights.get(child_light_id)
                    hue_children_ids.append(hue_child.id)

        if not hue_children_ids:
            _logger.warning("No children found for '%s' ('%s')!", hue_group.metadata.name, hue_group.id)

        return hue_children_ids

    def fetch_commands(self) -> bool:
        for device in self._devices.values():
            command = device.get_hue_command()
            if command:
                self._device_commands.append((device, command))
        return bool(self._device_commands)

    async def send_commands(self):
        while self._device_commands:
            device, command = self._device_commands.popleft()

            hue_item = self._cached_hue_items.get(device.hue_id)
            if hue_item:
                command = self._prepare_toggle_command(hue_item, command)

                try:
                    await self._send_command(hue_item, command)
                except HueException as ex:
                    _logger.warning("command failures ('%s', %s): %s", device.name, command, ex)
            # else: hue item does not exist, wrongly configured

    async def _send_command(self, hue_item: Union[Light, Room], command: HueCommand):
        # _logger.debug("send_device_command:\n%s\n%s", hue_item, command)

        command = self._prepare_dim_to_switch_off_command(hue_item, command)

        if isinstance(hue_item, Light):
            brightness: Optional[float] = None

            if command.type == HueCommandType.DIM:
                min_brightness = self._get_min_brightness(hue_item)
                on = command.dim >= min_brightness
                brightness = command.dim
            elif command.type == HueCommandType.SWITCH:
                on = True if command.switch == SwitchType.ON else False
            else:
                raise ValueError(f"Unsupported command ({command})!")

            await self._set_light(hue_item, on, brightness)

        elif isinstance(hue_item, Room):
            hue_children = self._get_lights_for_group(hue_item)
            for hue_child in hue_children:
                await self._send_command(hue_child, command)

    async def _set_light(self, hue_item: Light, on: Optional[bool], brightness: Optional[float]):
        try:
            await self._bridge.lights.set_state(hue_item.id, on=on, brightness=brightness)
        except aiohue.errors.AiohueException as ex:
            # further analysis needed!
            _logger.error("error bridge.lights.set_state(%s, %s, %s): %s", hue_item, on, brightness, ex)

    def _prepare_dim_to_switch_off_command(self, hue_item: Union[Light, Room], command: HueCommand) -> HueCommand:
        if command.type == HueCommandType.DIM:
            min_brightness = self._get_min_brightness(hue_item)
            if command.dim < min_brightness:  # Room | Light
                command = HueCommand.create_switch(SwitchType.OFF)
                return command
            elif isinstance(hue_item, Light) and not hue_item.supports_dimming:
                command = HueCommand.create_switch(SwitchType.ON)
                return command

        return command

    def _get_min_brightness(self, hue_item: Union[Light, Room]) -> float:
        device = self._devices.get(hue_item.id)
        min_brightness = device.min_brightness if device else 1

        if isinstance(hue_item, Light):
            if hue_item.supports_dimming and hue_item.dimming:
                if min_brightness < hue_item.dimming.min_dim_level:
                    min_brightness = hue_item.dimming.min_dim_level

        return min_brightness

    def _prepare_toggle_command(self, hue_item: Union[Light, Room], command: HueCommand) -> HueCommand:
        if command.type == HueCommandType.SWITCH and command.switch == SwitchType.TOGGLE:
            on_feature: OnFeature = None
            if isinstance(hue_item, Room):
                grouped_light_item = self._cached_hue_items.get(hue_item.grouped_light)
                if grouped_light_item and hasattr(grouped_light_item, "on") and isinstance(grouped_light_item.on, OnFeature):
                    on_feature = grouped_light_item.on
            elif isinstance(hue_item, Light):
                on_feature = hue_item.on

            if on_feature:
                command = HueCommand.create_switch(SwitchType.OFF if on_feature.on else SwitchType.ON)
            else:
                raise HueException("Cannot read OnFeature!")

        return command

    @classmethod
    def get_next_refresh_time(cls) -> datetime.datetime:
        return TimeUtils.now() + datetime.timedelta(seconds=600)
