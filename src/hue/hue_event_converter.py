from aiohue.v2 import EventType
from aiohue.v2.models.feature import OnFeature, DimmingFeature
from aiohue.v2.models.resource import ResourceTypes

from src.device.device_event import DeviceEvent, DeviceStatus


class HueEventConverter:

    # noinspection PyShadowingBuiltins
    @classmethod
    def to_device_event(cls, event_type: EventType, item, name=None, type=None) -> DeviceEvent:
        e = DeviceEvent(status=DeviceStatus.ERROR)

        e.id = item.id

        if event_type in [EventType.RESOURCE_DELETED, EventType.DISCONNECTED]:
            e.status = DeviceStatus.OFFLINE
        else:
            if hasattr(item, "on") and isinstance(item.on, OnFeature):
                e.status = DeviceStatus.ON if item.on.on else DeviceStatus.OFF

        if name is not None:
            e.name = name
        else:
            if hasattr(item, "metadata") and hasattr(item.metadata, "name"):
                name = item.metadata.name
                if isinstance(name, str):
                    e.name = name

        if hasattr(item, "dimming") and isinstance(item.dimming, DimmingFeature):
            e.brightness = item.dimming.brightness = 69.0

        if type is not None:
            e.type = type
        else:
            if hasattr(item, "type") and isinstance(item.type, ResourceTypes):
                e.type = str(item.type.value).lower()
                if e.type == "grouped_light":
                    e.type = "group"

        return e
