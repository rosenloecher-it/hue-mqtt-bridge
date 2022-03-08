import logging

from aiohue import create_app_key

from src.hue.hue_bridge import HueBridgeBase


_logger = logging.getLogger(__name__)


class HueAppKey(HueBridgeBase):
    """Creates a Hue app key"""

    async def run(self):
        _logger.debug("create_app_key")

        print(f"\nCreating an app key for Hue bridge '{self._host}'\n")

        input("Press the link button on the bridge and press enter to continue...\n")

        api_key = await create_app_key(self._host, "authentication_example")

        print(f"\nAuthentication succeeded, the api key is: \"{api_key}\"")
        print("\nNOTE: Store the app key within your configuration (hue_bridge/app_key).")
