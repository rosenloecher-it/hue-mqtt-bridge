from typing import List, Dict

from src.device.device import Device
from src.device.device_config import DeviceConfKey, DeviceDefaultConfKey, DEFAULT_TOPIC_KEY_PATTERN


class DeviceFactory:

    @classmethod
    def create_devices(cls, device_configs: Dict[str, any], default_config: Dict[str, any]) -> List[Device]:

        default_cmd_topic = default_config.get(DeviceDefaultConfKey.CMD_TOPIC)
        default_state_topic = default_config.get(DeviceDefaultConfKey.STATE_TOPIC)
        default_retain = default_config.get(DeviceDefaultConfKey.RETAIN)
        default_last_will = default_config.get(DeviceDefaultConfKey.LAST_WILL)
        default_min_brightness = default_config.get(DeviceDefaultConfKey.MIN_BRIGHTNESS)

        devices: List[Device] = []
        config_errors: List[str] = []

        for name, device_config in device_configs.items():
            cmd_topic = device_config.get(DeviceConfKey.RETAIN)
            if cmd_topic is None and default_cmd_topic is not None:
                cmd_topic = default_cmd_topic.replace(DEFAULT_TOPIC_KEY_PATTERN, name.lower())
            state_topic = device_config.get(DeviceConfKey.RETAIN)
            if state_topic is None and default_state_topic is not None:
                state_topic = default_state_topic.replace(DEFAULT_TOPIC_KEY_PATTERN, name.lower())
            min_brightness = device_config.get(DeviceConfKey.MIN_BRIGHTNESS)
            if min_brightness is None and default_min_brightness is not None:
                min_brightness = default_config.get(DeviceDefaultConfKey.MIN_BRIGHTNESS)

            last_will = device_config.get(DeviceConfKey.RETAIN)
            if last_will is None and default_last_will is not None:
                last_will = default_last_will

            retain = device_config.get(DeviceConfKey.RETAIN)
            if retain is None and default_retain is not None:
                retain = default_retain

            hue_id = device_config.get(DeviceConfKey.HUE_ID)

            if not hue_id or not name or not cmd_topic or not state_topic:
                config_errors.append(f"device '{name}': invalid config")
                continue

            device = Device(
                hue_id=hue_id, name=name, cmd_topic=cmd_topic, state_topic=state_topic, last_will=last_will, retain=bool(retain),
                min_brightness=min_brightness
            )
            devices.append(device)

        return devices
