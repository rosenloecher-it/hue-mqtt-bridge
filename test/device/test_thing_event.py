import unittest

from src.thing.thing_event import ThingEvent


class TestThingEvent(unittest.TestCase):

    def test_default_params(self):
        e1 = ThingEvent()
        e1.id = "e1"
        e1.brightness = 9

        e2 = ThingEvent()
        self.assertEqual(e2.id, None)
        self.assertEqual(e2.brightness, None)
