from __future__ import annotations

from typing import List
from unittest import IsolatedAsyncioTestCase

from src.hue.hue_config import HueBridgeConfKey
from src.hue.hue_explorer import HueExplorer
from test.hue.hue_bridge_simu import HueBridgeSimu


class HueExplorerSimu(HueExplorer):

    def __init__(self):
        config = {
            HueBridgeConfKey.HOST: "dummy_host",
            HueBridgeConfKey.APP_KEY: "dummy_app_key",
        }
        things = HueBridgeSimu.configurable_things()
        super().__init__(config, things)

        self.lines: List[str] = []

    async def _initialize_hue_bridge(self):
        self._bridge = HueBridgeSimu.create_hue_bridge()

    def print(self, text=""):
        self.lines.append(text)

    def count_occurrences(self, search: str) -> int:
        count = 0
        for line in self.lines:
            if search in line:
                count += 1
        return count

    @classmethod
    async def create(cls) -> HueExplorerSimu:
        connector = HueExplorerSimu()
        return connector


class TestHueExplorer(IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.explorer = await HueExplorerSimu.create()

    async def asyncTearDown(self):
        await self.explorer.close()

    async def test_explore(self):
        await self.explorer.run_tools()

        things = HueBridgeSimu.configurable_things()
        for thing in things:
            occurrences = self.explorer.count_occurrences(thing.name)
            self.assertGreaterEqual(occurrences, 5)  # name is used as id too, so very sophisticated
