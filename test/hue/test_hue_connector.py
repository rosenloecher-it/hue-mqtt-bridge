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
    def state_message(cls, hue_id: str, status: str, brightness=None):
        """generate an expected state message"""
        payload = {
            "name": hue_id,
            "status": status,
        }
        if brightness is not None:
            payload["brightness"] = brightness

        return StateMessage(
            topic=hue_id + "/state",
            payload=payload,
            retain=HueBridgeSimu.DEFAULT_RETAIN,
        )

    async def test_command_invalid(self):
        # noinspection SpellCheckingInspection
        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "afasfdsafa")
        self.connector.set_light.assert_not_called()
        result_messages = self.connector.get_state_message()
        self.assertEqual(result_messages, [])

    async def test_command_group_on_off(self):
        # switch on
        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "on")
        self.connector.set_light.assert_has_calls([
            call(id=HueBridgeSimu.ID_GROUP, on=True, brightness=None),
        ])

        # switch off
        self.connector.reset_actions()
        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "off")
        self.connector.set_light.assert_has_calls([
            call(id=HueBridgeSimu.ID_GROUP, on=False, brightness=None),
        ])

        # toggle on
        self.connector.reset_actions()
        self.connector.prepare_on_state(HueBridgeSimu.ID_GROUPED_LIGHT, False)
        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "toggle")
        self.connector.set_light.assert_has_calls([
            call(id=HueBridgeSimu.ID_GROUP, on=True, brightness=None),
        ])

        # toggle off
        self.connector.reset_actions()
        self.connector.prepare_on_state(HueBridgeSimu.ID_GROUPED_LIGHT, True)
        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "toggle")
        self.connector.set_light.assert_has_calls([
            call(id=HueBridgeSimu.ID_GROUP, on=False, brightness=None),
        ])

    async def test_command_group_dim(self):
        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "69")
        self.connector.set_light.assert_has_calls([
            call(id=HueBridgeSimu.ID_GROUP, on=True, brightness=69),
        ])

        # dim group off => switch off
        self.connector.reset_actions()
        await self.connector.simu_command(HueBridgeSimu.ID_GROUP, "15")
        self.connector.set_light.assert_has_calls([
            call(id=HueBridgeSimu.ID_GROUP, on=False, brightness=None),
        ])

    async def test_command_dim_to_switch(self):
        # dim => on
        await self.connector.simu_command(HueBridgeSimu.ID_SWITCH, "69")
        self.connector.set_light.assert_has_calls([
            call(id=HueBridgeSimu.ID_SWITCH, on=True, brightness=None),
        ])

        # dim => off
        self.connector.reset_actions()
        await self.connector.simu_command(HueBridgeSimu.ID_SWITCH, "5")
        self.connector.set_light.assert_has_calls([
            call(id=HueBridgeSimu.ID_SWITCH, on=False, brightness=None),
        ])

    async def test_on_state_changed_light(self):
        await self.connector.simu_on_state_changed(HueBridgeSimu.ID_SWITCH, True)

        result_messages = self.connector.get_state_message()
        self.assertCountEqual(result_messages, [
            self.state_message(HueBridgeSimu.ID_SWITCH, "on", brightness=None),
        ])

    async def test_on_state_changed_group(self):
        self.connector.prepare_dim_state(HueBridgeSimu.ID_COLOR1, 69)
        self.connector.prepare_on_state(HueBridgeSimu.ID_COLOR1, True)
        self.connector.prepare_dim_state(HueBridgeSimu.ID_COLOR2, 69)
        self.connector.prepare_on_state(HueBridgeSimu.ID_COLOR2, True)
        await self.connector.simu_on_state_changed(HueBridgeSimu.ID_GROUPED_LIGHT, True)

        result_messages = self.connector.get_state_message()
        self.assertCountEqual(result_messages, [
            self.state_message(HueBridgeSimu.ID_GROUP, "on", brightness=69),
        ])
