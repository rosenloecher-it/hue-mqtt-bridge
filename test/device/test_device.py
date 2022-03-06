import datetime
import unittest
from unittest import mock

from tzlocal import get_localzone

from src.device.device import Device
from src.device.device_event import DeviceEvent, DeviceStatus


class TestDevice(unittest.TestCase):

    # noinspection PyTypeChecker
    @mock.patch("src.time_utils.TimeUtils.now")
    def test_event_to_message(self, mocked_now):
        timestamp = datetime.datetime(2022, 1, 30, 10, 0, 0, tzinfo=get_localzone())
        mocked_now.return_value = timestamp

        e = DeviceEvent()
        e.id = "e1"
        e.name = "hue name"
        e.type = "light"
        e.status = DeviceStatus.OFF
        e.brightness = 68.9

        expected = {
            "brightness": 69,
            "id": e.id,
            "name": e.name,
            "type": e.type,
            "status": "off",
            "timestamp": timestamp.isoformat(),
        }

        message = Device.event_to_message(e)

        self.assertEqual(expected, message)
