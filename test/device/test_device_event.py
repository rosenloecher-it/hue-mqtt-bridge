import unittest

from src.device.device_event import DeviceEvent


class TestDeviceEvent(unittest.TestCase):

    def test_default_params(self):
        e1 = DeviceEvent()
        e1.id = "e1"
        e1.brightness = 9

        e2 = DeviceEvent()
        self.assertEqual(e2.id, None)
        self.assertEqual(e2.brightness, None)
