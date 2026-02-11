import unittest

from aiohue.v2 import EventType
from aiohue.v2.models.feature import AlertFeature, AlertEffectType, OnFeature, DimmingFeature, ColorFeature, ColorPoint, ColorGamut, \
    GamutType, DynamicsFeature, DynamicStatus
from aiohue.v2.models.grouped_light import GroupedLight
from aiohue.v2.models.light import Light, LightMode
from aiohue.v2.models.resource import ResourceIdentifier, ResourceTypes

from src.thing.thing_event import ThingEvent, ThingStatus
from src.hue.hue_event_converter import HueEventConverter


class TestHueEventConverter(unittest.TestCase):

    @classmethod
    def create_light_item_off(cls):
        return Light(
            id="2d157ce5-fe4c-4113-af2a-6afaa7d5a0cb",
            id_v1="/lights/9",
            on=OnFeature(on=False),
            dimming=DimmingFeature(brightness=69.0, min_dim_level=10.0),
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
            owner=ResourceIdentifier(rid="ba670a08-e717-43eb-9cfd-5c1613bb85f2", rtype=ResourceTypes.DEVICE),
        )

    @classmethod
    def create_grouped_light_item_on(cls) -> GroupedLight:
        id = "7a335802-b3d0-40bf-8f85-b7c11307fa50"
        return GroupedLight(
            id=id,
            id_v1="/groups/9",
            on=OnFeature(on=True),
            alert=AlertFeature(action_values=[AlertEffectType.BREATHE]),
            type=ResourceTypes.GROUPED_LIGHT,
            owner=ResourceIdentifier(rid=id, rtype=ResourceTypes.GROUPED_LIGHT),
        )

    def test_light_item(self):
        for is_on, expected_brightness in [(True, 69.0), (False, 0)]:
            hue_item = self.create_light_item_off()
            hue_item.on.on = is_on

            event_exp = ThingEvent()
            event_exp.id = hue_item.id

            # event_exp.name = None  # name has to be matched via device
            event_exp.type = "light"
            event_exp.status = ThingStatus.ON if is_on else ThingStatus.OFF
            event_exp.brightness = expected_brightness

            event_out = HueEventConverter.to_thing_event(EventType.RESOURCE_UPDATED, hue_item)
            self.assertEqual(event_exp, event_out)

    def test_grouped_light_item_on(self):
        hue_item = self.create_grouped_light_item_on()

        event_exp = ThingEvent()
        event_exp.id = hue_item.id
        event_exp.type = "group"
        event_exp.status = ThingStatus.ON

        event_out = HueEventConverter.to_thing_event(EventType.RESOURCE_UPDATED, hue_item)
        self.assertEqual(event_exp, event_out)
