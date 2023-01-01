import datetime
import unittest
from unittest import mock

from tzlocal import get_localzone

from src.thing.thing_event import ThingEvent, ThingStatus


class TestThingEvent(unittest.TestCase):

    def test_default_params(self):
        e1 = ThingEvent()
        e1.id = "e1"
        e1.brightness = 9

        e2 = ThingEvent()
        self.assertEqual(e2.id, None)
        self.assertEqual(e2.brightness, None)

    # noinspection PyTypeChecker
    @mock.patch("src.utils.time_utils.TimeUtils.now")
    def test_event_to_message(self, mocked_now):
        timestamp = datetime.datetime(2022, 1, 30, 10, 0, 0, tzinfo=get_localzone())
        mocked_now.return_value = timestamp

        e = ThingEvent()
        e.id = "e1"
        e.name = "hue name"
        e.type = "light"
        e.status = ThingStatus.OFF
        e.brightness = 68.9

        expected = {
            "brightness": 69,
            "name": e.name,
            "status": "off",
            "timestamp": timestamp,
        }

        message_data = e.to_data()

        self.assertEqual(expected, message_data)
