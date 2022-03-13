from __future__ import annotations

from unittest import IsolatedAsyncioTestCase
from unittest.mock import call

from src.thing.thing import StateMessage
from test.hue.hue_bridge_simu import HueBridgeSimu
from test.hue.hue_connector_simu import HueConnectorSimu


class TestHueConnector(IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.connector = await HueConnectorSimu.create()

    async def asyncTearDown(self):
        await self.connector.close()

    @classmethod
    def state_message(cls, hue_id: str, status: str, hue_type="light", brightness=None):
        """generate an expected state message"""
        payload = {
            "id": hue_id,
            "name": hue_id,
            "status": status,
            "type": hue_type,
        }
        if brightness is not None:
            payload["brightness"] = brightness

        return StateMessage(
            topic=hue_id + "/state",
            payload=payload,
            retain=HueBridgeSimu.DEFAULT_RETAIN,
        )

    async def test_invalid_command(self):
        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "afasfdsafa")
        self.connector.set_light.assert_not_called()
        result_messages = self.connector.get_state_message()
        self.assertEqual(result_messages, [])

    async def test_group_on_off(self):
        calls_on = [
            call(id=HueBridgeSimu.ID_COLOR1, on=True, brightness=None),
            call(id=HueBridgeSimu.ID_COLOR2, on=True, brightness=None),
        ]
        calls_off = [
            call(id=HueBridgeSimu.ID_COLOR1, on=False, brightness=None),
            call(id=HueBridgeSimu.ID_COLOR2, on=False, brightness=None),
        ]
        expected_messages_on = [
            self.state_message(HueBridgeSimu.ID_COLOR1, "on", brightness=100),
            self.state_message(HueBridgeSimu.ID_COLOR2, "on", brightness=100),
            self.state_message(HueBridgeSimu.ID_GROUP, "on", hue_type="group", brightness=100),
        ]
        expected_messages_off = [
            self.state_message(HueBridgeSimu.ID_COLOR1, "off", brightness=0),
            self.state_message(HueBridgeSimu.ID_COLOR2, "off", brightness=0),
            self.state_message(HueBridgeSimu.ID_GROUP, "off", hue_type="group", brightness=0),
        ]

        # switch on
        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "on")
        self.connector.set_light.assert_has_calls(calls_on)
        result_messages = self.connector.get_state_message()
        self.assertCountEqual(result_messages, expected_messages_on)

        # switch off
        self.connector.reset_actions()
        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "off")
        self.connector.set_light.assert_has_calls(calls_off)
        result_messages = self.connector.get_state_message()
        self.assertCountEqual(result_messages, expected_messages_off)

        # toogle on
        self.connector.reset_actions()
        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "toggle")
        self.connector.set_light.assert_has_calls(calls_on)
        result_messages = self.connector.get_state_message()
        self.assertCountEqual(result_messages, expected_messages_on)

        # toggle off
        self.connector.reset_actions()
        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "toggle")
        self.connector.set_light.assert_has_calls(calls_off)
        result_messages = self.connector.get_state_message()
        self.assertCountEqual(result_messages, expected_messages_off)

    async def test_group_dim(self):
        calls_69 = [
            call(id=HueBridgeSimu.ID_COLOR1, on=True, brightness=69),
            call(id=HueBridgeSimu.ID_COLOR2, on=True, brightness=69),
        ]
        calls_off = [
            call(id=HueBridgeSimu.ID_COLOR1, on=False, brightness=None),
            call(id=HueBridgeSimu.ID_COLOR2, on=False, brightness=None),
        ]
        expected_messages_69 = [
            self.state_message(HueBridgeSimu.ID_COLOR1, "on", brightness=69),
            self.state_message(HueBridgeSimu.ID_COLOR2, "on", brightness=69),
            self.state_message(HueBridgeSimu.ID_GROUP, "on", hue_type="group", brightness=69),
        ]
        expected_messages_off = [
            self.state_message(HueBridgeSimu.ID_COLOR1, "off", brightness=0),
            self.state_message(HueBridgeSimu.ID_COLOR2, "off", brightness=0),
            self.state_message(HueBridgeSimu.ID_GROUP, "off", hue_type="group", brightness=0),
        ]

        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "69")
        self.connector.set_light.assert_has_calls(calls_69)
        result_messages = self.connector.get_state_message()
        self.assertCountEqual(result_messages, expected_messages_69)

        # dim group off => switch off
        self.connector.reset_actions()
        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "15")
        self.connector.set_light.assert_has_calls(calls_off)
        result_messages = self.connector.get_state_message()
        self.assertCountEqual(result_messages, expected_messages_off)

        # dim on again
        self.connector.reset_actions()
        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "69")
        self.connector.set_light.assert_has_calls(calls_69)
        result_messages = self.connector.get_state_message()
        self.assertCountEqual(result_messages, expected_messages_69)

    async def test_switch_dim(self):
        """the switch down not supports dimming and is supposed to toggle around the configured min brightness"""
        calls_on = [
            call(id=HueBridgeSimu.ID_SWITCH, on=True, brightness=None),
        ]
        calls_off = [
            call(id=HueBridgeSimu.ID_SWITCH, on=False, brightness=None),
        ]
        expected_messages_on = [
            self.state_message(HueBridgeSimu.ID_SWITCH, "on", brightness=None),
        ]
        expected_messages_off = [
            self.state_message(HueBridgeSimu.ID_SWITCH, "off", brightness=None),
        ]

        # dim => on
        await self.connector.simu_command(HueBridgeSimu.ID_SWITCH, "69")
        self.connector.set_light.assert_has_calls(calls_on)
        result_messages = self.connector.get_state_message()
        self.assertEqual(result_messages, expected_messages_on)

        # dim => off
        self.connector.reset_actions()
        await self.connector.simu_command(HueBridgeSimu.ID_SWITCH, "5")
        self.connector.set_light.assert_has_calls(calls_off)
        result_messages = self.connector.get_state_message()
        self.assertEqual(result_messages, expected_messages_off)
