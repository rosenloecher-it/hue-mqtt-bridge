from typing import List, Dict

from src.app_config import ConfigException
from src.thing.thing import Thing
from src.thing.thing_config import ThingConfKey, ThingDefaultConfKey, DEFAULT_TOPIC_KEY_PATTERN


class ThingFactory:

    @classmethod
    def create_things(cls, thing_configs: Dict[str, any], default_config: Dict[str, any]) -> List[Thing]:

        default_cmd_topic = default_config.get(ThingDefaultConfKey.CMD_TOPIC)
        default_state_topic = default_config.get(ThingDefaultConfKey.STATE_TOPIC)
        default_retain = default_config.get(ThingDefaultConfKey.RETAIN)
        default_last_will = default_config.get(ThingDefaultConfKey.LAST_WILL)
        default_min_brightness = default_config.get(ThingDefaultConfKey.MIN_BRIGHTNESS)

        things: List[Thing] = []

        for name, thing_config in thing_configs.items():
            cmd_topic = thing_config.get(ThingConfKey.CMD_TOPIC)
            if cmd_topic is None and default_cmd_topic is not None:
                cmd_topic = default_cmd_topic.replace(DEFAULT_TOPIC_KEY_PATTERN, name.lower())
            state_topic = thing_config.get(ThingConfKey.STATE_TOPIC)
            if state_topic is None and default_state_topic is not None:
                state_topic = default_state_topic.replace(DEFAULT_TOPIC_KEY_PATTERN, name.lower())
            min_brightness = thing_config.get(ThingConfKey.MIN_BRIGHTNESS)
            if min_brightness is None and default_min_brightness is not None:
                min_brightness = default_config.get(ThingDefaultConfKey.MIN_BRIGHTNESS)

            last_will = thing_config.get(ThingConfKey.LAST_WILL)
            if last_will is None and default_last_will is not None:
                last_will = default_last_will

            retain = thing_config.get(ThingConfKey.RETAIN)
            if retain is None and default_retain is not None:
                retain = default_retain

            hue_id = thing_config.get(ThingConfKey.HUE_ID)

            if not cmd_topic and not state_topic:
                raise ConfigException(f"Thing '{name}' has no MQTT topics!")

            thing = Thing(
                hue_id=hue_id, name=name, cmd_topic=cmd_topic, state_topic=state_topic, last_will=last_will, retain=bool(retain),
                min_brightness=min_brightness
            )
            things.append(thing)

        return things
