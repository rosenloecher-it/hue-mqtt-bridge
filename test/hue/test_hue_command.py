import unittest

from src.hue.hue_command import HueCommand, SwitchType


class TestHueCommand(unittest.TestCase):

    def test_parse(self):
        command = HueCommand.parse(" On ")
        self.assertEqual(command, HueCommand.create_switch(SwitchType.ON))

        command = HueCommand.parse(" tRue ")
        self.assertEqual(command, HueCommand.create_switch(SwitchType.ON))

        command = HueCommand.parse(" oFF ")
        self.assertEqual(command, HueCommand.create_switch(SwitchType.OFF))

        command = HueCommand.parse(" falsE ")
        self.assertEqual(command, HueCommand.create_switch(SwitchType.OFF))

        command = HueCommand.parse(" 0 ")
        self.assertEqual(command, HueCommand.create_switch(SwitchType.OFF))

        command = HueCommand.parse(" toggle ")
        self.assertEqual(command, HueCommand.create_switch(SwitchType.TOGGLE))

        command = HueCommand.parse(" 90 ")
        self.assertEqual(command, HueCommand.create_dim(90))

        with self.assertRaises(ValueError):
            HueCommand.parse("200")

        with self.assertRaises(ValueError):
            HueCommand.parse(" sadcsdafc ")
