import datetime
import logging
from collections import deque
from typing import Optional, List, Dict, Set, Union, Deque

import aiohue
import attr
import rx
from aiohue import HueBridgeV2
from aiohue.v2 import EventType
from aiohue.v2.models.feature import OnFeature
from aiohue.v2.models.grouped_light import GroupedLight
from aiohue.v2.models.light import Light
from aiohue.v2.models.room import Room
from rx import operators as rx_ops
from rx.core import Observer
from rx.disposable import Disposable

from src.app_config import ConfigException
from src.hue.hue_command import HueCommand, HueCommandType, SwitchType
from src.hue.hue_config import HueBridgeConfKey, HueBridgeDefaults
from src.hue.hue_event_converter import HueEventConverter
from src.thing.thing import Thing
from src.thing.thing_event import ThingEvent
from src.utils.time_utils import TimeUtils

_logger = logging.getLogger(__name__)


class HueException(Exception):
    pass


@attr.frozen
class StateChange:

    event_type: any
    item: any


class HueConnectorBase:

    def __init__(self, config, things: List[Thing]):

        self._host = config[HueBridgeConfKey.HOST]
        self._app_key = config[HueBridgeConfKey.APP_KEY]
        self._things: Dict[str, Thing] = {}

        self._bridge: Optional[HueBridgeV2] = None

        for thing in things:
            existing_thing = self._things.get(thing.hue_id)
            if existing_thing:
                raise ConfigException(f"Hue item '{thing.hue_id}' is already registered as thing '{thing.name}'!")
            self._things[thing.hue_id] = thing

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
        # do nothing in base implementation!


class HueConnector(HueConnectorBase):

    def __init__(self, config, things: List[Thing]):
        super().__init__(config, things)

        self._group_debounce_time = config.get(HueBridgeConfKey.GROUP_DEBOUNCE_TIME, HueBridgeDefaults.GROUP_DEBOUNCE_TIME) / 1000

        self._thing_commands: Deque[(Thing, HueCommand)] = deque()

        self._group_children: Dict[str, List[str]] = {}
        self._grouped_light_to_group: Dict[str, str] = {}
        self._hue_items: Dict[str, Union[Light, GroupedLight]] = {}
        self._light_to_group: Dict[str, str] = {}

        self._group_observers: Dict[str, Optional[Observer]] = {}  # group id: observer
        self._state_observers: Dict[str, Optional[Observer]] = {}  # thing id: observer
        self._disposables: List[Disposable] = []

        self._next_refresh_time = self.get_next_refresh_time()

    async def connect(self):
        await self._initialize_hue_bridge()

        self._rebuild_caches()
        self._next_refresh_time = self.get_next_refresh_time()

    async def close(self):
        await super().close()

        self._close_debounces()
        self._hue_items = {}

    async def _initialize_hue_bridge(self):
        await super()._initialize_hue_bridge()

        self._bridge.subscribe(self._on_state_changed)

    def _rebuild_caches(self):
        self._group_children = {}
        self._grouped_light_to_group = {}
        self._hue_items = {}
        self._light_to_group: Dict[str, str] = {}

        self._close_debounces()

        # prepare cache first just in case
        for hue_light in self._bridge.lights:
            self._hue_items[hue_light.id] = hue_light
        for hue_group in self._bridge.groups:
            self._hue_items[hue_group.id] = hue_group

        # initialized groups
        for hue_group in self._bridge.groups:
            thing = self._things.get(hue_group.id)
            if thing:
                if not isinstance(hue_group, Room):  # Zone is inherited from Room
                    _logger.warning("Only 'Rooms/Zones' are supported as groups. '%s' is of type '%s'. It's ignored!", type(hue_group))
                    del self._things[hue_group.id]
                    continue

                self._grouped_light_to_group[hue_group.grouped_light] = hue_group.id

                hue_children_ids = self._find_lights_for_group(hue_group)
                self._group_children[hue_group.id] = hue_children_ids

                for hue_children_id in hue_children_ids:
                    self._light_to_group[hue_children_id] = hue_group.id

                self._register_group_debounce(hue_group)

        not_found_items = []
        for thing in self._things.values():
            if not self._hue_items.get(thing.hue_id):
                not_found_items.append(f"hue id: {thing.hue_id}, thing: {thing.name}")
                thing.close()  # sends last will if configured
            else:
                self._register_state_debounce(thing)
        if not_found_items:
            _logger.warning("Unknown hue items found (%s)!", ", ".join(not_found_items))

        # feed devices last. the debounce pipes get triggered in parallel
        for hue_light in self._bridge.lights:
            self._on_state_changed(EventType.RESOURCE_UPDATED, hue_light)
        for hue_group in self._bridge.groups:
            if isinstance(hue_group, GroupedLight):
                self._on_state_changed(EventType.RESOURCE_UPDATED, hue_group)
        for hue_group in self._bridge.groups:
            if not isinstance(hue_group, GroupedLight):
                self._on_state_changed(EventType.RESOURCE_UPDATED, hue_group)

    def _close_debounces(self):
        for observable in self._group_observers.values():
            observable.on_completed()
        self._group_observers = {}

        for observable in self._state_observers.values():
            observable.on_completed()
        self._state_observers = {}

        for disposable in self._disposables:
            disposable.dispose()
        self._disposables = []

    def _register_state_debounce(self, thing: Thing):
        thing_id = thing.hue_id

        def creating_observer_callback(observer, _):
            self._state_observers[thing_id] = observer

        def feed_state_update(thing_event: ThingEvent):
            thing_inner = self._things.get(thing_id)
            if thing_inner:
                thing_inner.process_state_change(thing_event)
            else:
                _logger.debug('No "debounced state update"" possible: thing id (%s) not found!', thing_id)
            pass

        observable = rx.create(creating_observer_callback)

        disposable = observable.pipe(
            rx_ops.debounce(thing.state_debounce_time)
        ).subscribe(lambda thing_event: feed_state_update(thing_event))

        self._disposables.append(disposable)

    def _register_group_debounce(self, hue_group: Room):
        group_id = hue_group.id

        def creating_observer_callback(observer, _):
            group_id_inner = group_id
            self._group_observers[group_id_inner] = observer

        def feed_group_update():
            group_id_inner = group_id
            hue_group_inner = self._hue_items.get(group_id_inner)
            if hue_group_inner:
                self._on_state_changed(EventType.RESOURCE_UPDATED, hue_group_inner)
            else:
                _logger.debug('No "debounced group update"" possible: group id (%s) not found! Just refreshing...?', group_id_inner)

        observable = rx.create(creating_observer_callback)

        disposable = observable.pipe(
            rx_ops.debounce(self._group_debounce_time)
        ).subscribe(lambda _: feed_group_update())

        self._disposables.append(disposable)

    def _trigger_group_debounce(self, group_id):
        observer = self._group_observers.get(group_id)
        if observer:
            observer.on_next(group_id)
        else:
            _logger.warning("'group debounce' failed, because group (%s) was not found!", group_id)

    def _on_state_changed(self, event_type: EventType, item):
        if not item or not item.id:
            _logger.debug("skipped 'on_state_changed' because an invalid item.")
            return

        # _logger.debug("_on_state_changed - in: %s, %s", event_type, item)

        self._hue_items[item.id] = item

        if isinstance(item, GroupedLight):
            group_id = self._grouped_light_to_group.get(item.id)
            if group_id:
                self._trigger_group_debounce(group_id)
            return  # event is prepared and sent when group gets through

        if isinstance(item, Light):
            group_id = self._light_to_group.get(item.id)
            if group_id:
                self._trigger_group_debounce(group_id)

        group_item = None
        event_item = item
        thing = self._things.get(item.id)
        if not thing:
            return

        if isinstance(item, Room):
            group_item = item
            event_item = self._hue_items.get(group_item.grouped_light)
            if not event_item:
                _logger.warning("cannot found group light for '%s'", thing.name)
                return

        thing_event = HueEventConverter.to_thing_event(event_type, event_item, thing.name)
        if group_item is not None:
            thing_event.id = thing.hue_id
            thing_event.name = thing.name
            thing_event.brightness = self._get_average_brightness_for_group(group_item)

        # _logger.debug("_on_state_changed: %s, %s => %s", event_type, item, thing_event)
        observer = self._state_observers.get(thing.hue_id)
        if observer:
            observer.on_next(thing_event)

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
        hue_children_ids = self._group_children.get(hue_group.id)
        hue_children = []
        for hue_child_id in hue_children_ids:
            hue_child = self._hue_items.get(hue_child_id)
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
        for device in self._things.values():
            command = device.get_hue_command()
            if command:
                self._thing_commands.append((device, command))
        return bool(self._thing_commands)

    async def send_commands(self):
        while self._thing_commands:
            device, command = self._thing_commands.popleft()

            hue_item = self._hue_items.get(device.hue_id)
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
        device = self._things.get(hue_item.id)
        min_brightness = device.min_brightness if device else 1

        if isinstance(hue_item, Light):
            if hue_item.dimming and hue_item.dimming.min_dim_level is not None:
                if min_brightness < hue_item.dimming.min_dim_level:
                    min_brightness = hue_item.dimming.min_dim_level

        return min_brightness

    def _prepare_toggle_command(self, hue_item: Union[Light, Room], command: HueCommand) -> HueCommand:
        if command.type == HueCommandType.SWITCH and command.switch == SwitchType.TOGGLE:
            on_feature: OnFeature = None
            if isinstance(hue_item, Room):
                grouped_light_item = self._hue_items.get(hue_item.grouped_light)
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
        return TimeUtils.now() + datetime.timedelta(seconds=1800)
