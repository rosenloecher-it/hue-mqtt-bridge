import uuid
from typing import List
from unittest.mock import MagicMock

from aiohue.v2 import HueBridgeV2
from aiohue.v2.models.device import DeviceProductData, DeviceArchetypes, DeviceMetaData, Device
from aiohue.v2.models.feature import AlertFeature, AlertEffectType, OnFeature, DimmingFeature, ColorFeature, ColorPoint, ColorGamut, \
    GamutType, DynamicsFeature, DynamicStatus
from aiohue.v2.models.grouped_light import GroupedLight
from aiohue.v2.models.light import Light, LightMetaData, LightMode
from aiohue.v2.models.resource import ResourceIdentifier, ResourceTypes
from aiohue.v2.models.room import Room

import src.device.device as app_device


class _SimuDefault:
    """only purpose of this class is forward declaration for the devices"""

    MIN_DIM_LIGHT = 10.0
    MIN_DIM_GROUP = 20.0

    DEFAULT_RETAIN = True


class DeviceSimu(app_device.Device):

    def __init__(self, hue_item, min_brightness):
        super().__init__(
            hue_id=hue_item.id,
            name=hue_item.id,
            cmd_topic=hue_item.id + "/cmd",
            state_topic=hue_item.id + "/state",
            last_will=None,
            retain=_SimuDefault.DEFAULT_RETAIN,
            min_brightness=min_brightness
        )

        self.hue_item = hue_item


class LightSimu(DeviceSimu):

    def __init__(self, hue_item, hue_device: Device, hue_room=None):
        super().__init__(hue_item, _SimuDefault.MIN_DIM_LIGHT)

        if not isinstance(hue_item, Light):
            raise ValueError("No Light")

        self.hue_device: Device = hue_device
        self.hue_room: Room = hue_room


class RoomSimu(DeviceSimu):

    def __init__(self, hue_item, hue_lights: List[Light], hue_grouped_light: GroupedLight):
        super().__init__(hue_item, _SimuDefault.MIN_DIM_GROUP)

        if not isinstance(hue_item, Room):
            raise ValueError("No Room")

        self.hue_lights: List[Light] = list(hue_lights)
        self.hue_grouped_light: GroupedLight = hue_grouped_light


class HueBridgeSimu:
    """
    Creates a "HueBridgeV2" bridge with devices, lights, rooms, "grouped lights"...

    Structure:
    - switch
    - dimmer
    - group
        - color1
        - color2
    """

    ID_SWITCH = "switch"  # single light
    ID_DIMMER = "dimmer"  # single light
    ID_GROUP = "group"
    ID_COLOR1 = "color1"  # assigned to "group"
    ID_COLOR2 = "color2"  # assigned to "group"

    MIN_DIM_LIGHT = _SimuDefault.MIN_DIM_LIGHT
    MIN_DIM_GROUP = _SimuDefault.MIN_DIM_GROUP
    DEFAULT_RETAIN = _SimuDefault.DEFAULT_RETAIN

    @classmethod
    def create_hue_bridge(cls) -> HueBridgeV2:
        bridge = MagicMock(HueBridgeV2, autospec=True)

        hue_devices = []
        hue_lights = []
        hue_groups = []

        config_devices = cls.configurable_devices()
        for config_device in config_devices:

            if isinstance(config_device, LightSimu):
                hue_lights.append(config_device.hue_item)
                hue_devices.append(config_device.hue_device)

            elif isinstance(config_device, RoomSimu):
                hue_groups.append(config_device.hue_item)
                hue_groups.append(config_device.hue_grouped_light)

            else:
                raise ValueError("Wrong type")

        bridge.devices = hue_devices
        bridge.lights = hue_lights
        bridge.groups = hue_groups
        bridge.sensors = []

        return bridge

    @classmethod
    def configurable_devices(cls) -> List[app_device.Device]:
        switch_device_id = "device-" + cls.ID_SWITCH
        hue_item = cls.create_hue_switch_light(cls.ID_SWITCH, switch_device_id)
        hue_device = cls.create_hue_device(switch_device_id, hue_item.id)
        simu_switch = LightSimu(hue_item, hue_device)

        switch_device_id = "device-" + cls.ID_DIMMER
        hue_item = cls.create_hue_dim_light(cls.ID_DIMMER, switch_device_id)
        hue_device = cls.create_hue_device(switch_device_id, hue_item.id)
        simu_dimmer = LightSimu(hue_item, hue_device)

        switch_device_id = "device-" + cls.ID_COLOR1
        hue_color1 = cls.create_hue_color_light(cls.ID_COLOR1, switch_device_id)
        hue_device1 = cls.create_hue_device(switch_device_id, hue_color1.id)

        switch_device_id = "device-" + cls.ID_COLOR2
        hue_color2 = cls.create_hue_color_light(cls.ID_COLOR2, switch_device_id)
        hue_device2 = cls.create_hue_device(switch_device_id, hue_color2.id)

        hue_grouped_light = cls.create_hue_group_light("grouped_light-" + cls.ID_GROUP)
        hue_room = cls.create_hue_room(
            cls.ID_GROUP,
            light_device_ids=[hue_device1.id, hue_device2.id],
            grouped_light_id=hue_grouped_light.id
        )

        simu_room = RoomSimu(hue_room, [hue_color1, hue_color2], hue_grouped_light)
        simu_color1 = LightSimu(hue_color1, hue_device1, hue_room)
        simu_color2 = LightSimu(hue_color2, hue_device2, hue_room)

        devices = [simu_switch, simu_dimmer, simu_room, simu_color1, simu_color2]
        return devices

    @classmethod
    def create_hue_device(cls, device_id: str, light_id: str):

        return Device(
            id=device_id,
            id_v1="",
            type=ResourceTypes.DEVICE,
            services=[
                ResourceIdentifier(rid=light_id, rtype=ResourceTypes.LIGHT),
                ResourceIdentifier(rid=str(uuid.uuid4()), rtype=ResourceTypes.ZIGBEE_CONNECTIVITY),
                ResourceIdentifier(rid=str(uuid.uuid4()), rtype=ResourceTypes.ENTERTAINMENT),
            ],
            product_data=DeviceProductData(
                model_id=device_id,
                manufacturer_name='manufacturer_name',
                product_name='product_name',
                product_archetype=DeviceArchetypes.HUE_LIGHTSTRIP,
                certified=True,
                software_version='1.2.3'
            ),
            metadata=DeviceMetaData(archetype=DeviceArchetypes.HUE_LIGHTSTRIP, name=device_id),
        )

    @classmethod
    def create_hue_room(cls, test_id: str, light_device_ids: List[str], grouped_light_id: str):

        services = []
        children = []

        for light_device_id in light_device_ids:
            services.append(ResourceIdentifier(rid=light_device_id, rtype=ResourceTypes.LIGHT))
            children.append(ResourceIdentifier(rid=light_device_id, rtype=ResourceTypes.DEVICE))

        services.append(ResourceIdentifier(rid=grouped_light_id, rtype=ResourceTypes.GROUPED_LIGHT))

        return Room(
            id=test_id,
            id_v1=f"/lights/{test_id}",
            metadata=LightMetaData(archetype="icon", name=test_id),
            type=ResourceTypes.ROOM,
            services=services,
            children=children,
        )

    @classmethod
    def create_hue_group_light(cls, test_id: str):
        return GroupedLight(
            id=test_id,
            id_v1=f"/lights/{test_id}",
            on=OnFeature(on=False),
            alert=AlertFeature(action_values=[AlertEffectType.BREATHE]),
            type=ResourceTypes.GROUPED_LIGHT,
        )

    @classmethod
    def create_hue_color_light(cls, light_id: str, device_id: str):
        return Light(
            id=light_id,
            id_v1=f"/lights/{light_id}",
            metadata=LightMetaData(archetype="icon", name=light_id),
            on=OnFeature(on=False),
            dimming=DimmingFeature(brightness=100.0, min_dim_level=cls.MIN_DIM_LIGHT),
            color_temperature=None,
            color=ColorFeature(
                xy=ColorPoint(x=0.502, y=0.44),
                gamut_type=GamutType.A,
                gamut=ColorGamut(
                    red=ColorPoint(x=0.704, y=0.296),
                    green=ColorPoint(x=0.2151, y=0.7106),
                    blue=ColorPoint(x=0.138, y=0.08)
                )
            ),
            mode=LightMode.NORMAL,
            type=ResourceTypes.LIGHT,
            alert=AlertFeature(action_values=[AlertEffectType.BREATHE]),
            dynamics=DynamicsFeature(
                speed=0.0,
                speed_valid=False,
                status=DynamicStatus.NONE,
                status_values=[DynamicStatus.NONE, DynamicStatus.DYNAMIC_PALETTE]
            ),
            effects=None,
            gradient=None,
            owner=ResourceIdentifier(rid=device_id, rtype=ResourceTypes.DEVICE),
        )

    @classmethod
    def create_hue_dim_light(cls, light_id: str, device_id: str):
        hue_light = cls.create_hue_color_light(light_id, device_id)

        hue_light.color = None
        hue_light.color_temperature = None

        return hue_light

    @classmethod
    def create_hue_switch_light(cls, light_id: str, device_id: str):
        hue_light = cls.create_hue_color_light(light_id, device_id)

        hue_light.color = None
        hue_light.color_temperature = None
        hue_light.dimming = None

        return hue_light

    # @classmethod
    # def set_ligth(cls, light: Light, on=Optional[False], brightness=Optional[float]):
    #     pass
    #
    # @classmethod
    # def set_room(cls, light: Light, on=Optional[False], brightness=Optional[float]):
    #     pass
