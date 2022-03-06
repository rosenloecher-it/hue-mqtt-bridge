import logging

from aiohue import create_app_key
from aiohue.discovery import discover_nupnp
from aiohue.v2.models.room import Room

from src.hue.hue_bridge import HueBridgeBase


_logger = logging.getLogger(__name__)


class HueTools(HueBridgeBase):

    async def create_app_key(self):
        _logger.debug("create_app_key")

        print(f"\nCreating an app key for Hue bridge '{self._host}'\n")

        input("Press the link button on the bridge and press enter to continue...")

        api_key = await create_app_key(self._host, "authentication_example")

        print(f"\nAuthentication succeeded, the api key is: \"{api_key}\"")
        print("\nNOTE: Store the app key within your configuration (hue_bridge/app_key).")

    @classmethod
    async def discover(cls):
        _logger.debug("discover")
        print("\nDiscovering Hue bridges...\n")

        bridges = await discover_nupnp()
        if bridges:
            for bridge in bridges:
                support_info = "" if bridge.supports_v2 else "; NOT supported (no V2)!"
                print(f"Found bridge: IP '{bridge.host}'; ID '{bridge.id}'{support_info}")
        else:
            print("No bridge found.")

        print()

    async def explore(self):
        if not self._bridge:
            await self.connect()

        b = self._bridge

        print(f"Explore Hue bridge '{self._host}':")
        print(f"    id: {b.bridge_id}")
        print(f"    name: {b.config.name}")
        print(f"    model: {b.config.model_id}")
        print(f"    api version: {b.config.software_version}")

        print()
        print("Hue devices")
        for item in b.devices:
            print(f"    id: '{item.id}' ('{item.id_v1}'); name: '{item.metadata.name}'")
            for child_id in item.lights:
                print(f"        id: '{child_id}'")

        print()
        print("Hue groups")
        for item in b.groups:
            if isinstance(item, Room):
                print(f"    id: '{item.id}' ('{item.id_v1}'); name: '{item.metadata.name}'; type: {item.type.name}")
                for child in item.children:
                    print(f"        id: '{child.rid}'")
            else:
                print(f"    id: '{item.id}' ('{item.id_v1}'); type: {item.type.name}")

        print()
        print("Lights")
        for item in b.lights:
            print(f"    id: '{item.id}' ('{item.id_v1}'); name: '{item.metadata.name}'; color: {item.supports_color}; "
                  f"color_temp: {item.supports_color_temperature}; dimming: {item.supports_dimming}")

        print()

        # TODO evaluate self._devices
