
import unittest

from jsonschema import validate

from src.thing.thing_config import DEFAULT_TOPIC_KEY_PATTERN, THING_DEFAULTS_JSONSCHEMA, THINGS_JSONSCHEMA
from src.thing.thing_factory import ThingFactory


class TestThingFactory(unittest.TestCase):

    def test_create_things(self):
        thing_defaults_config = {
            "state_topic": f"test/hue/{DEFAULT_TOPIC_KEY_PATTERN}/state",
            "cmd_topic": f"test/hue/{DEFAULT_TOPIC_KEY_PATTERN}/cmd",
            "last_will": '{"status": "offline"}',
            "retain": True,
            "min_brightness": 15,
        }
        default_thing_config = {"hue_id": "default_thing"}
        specialized_thing_config = {
            "hue_id": "specialized_thing",
            "state_topic": "specialized_thing/state",
            "cmd_topic": "specialized_thing/cmd",
            "last_will": "specialized_thing is offline",
            "retain": False,
            "min_brightness": 45,
        }

        things_config = {
            "default_thing": default_thing_config,
            "specialized_thing": specialized_thing_config,
        }

        validate(thing_defaults_config, THING_DEFAULTS_JSONSCHEMA)
        validate(things_config, THINGS_JSONSCHEMA)

        things = ThingFactory.create_things(things_config, thing_defaults_config)
        self.assertEqual(len(things), 2)
        default_thing = next(filter(lambda t: t.name == "default_thing", things))
        specialized_thing = next(filter(lambda t: t.name == "specialized_thing", things))

        self.assertEqual(default_thing.hue_id, default_thing_config["hue_id"])
        self.assertEqual(default_thing.name, "default_thing")
        self.assertEqual(default_thing.cmd_topic, f"test/hue/{default_thing.name}/cmd")
        self.assertEqual(default_thing.last_will, thing_defaults_config["last_will"])
        self.assertEqual(default_thing.min_brightness, thing_defaults_config["min_brightness"])
        self.assertEqual(default_thing.retain, thing_defaults_config["retain"])
        self.assertEqual(default_thing.state_topic, f"test/hue/{default_thing.name}/state")

        self.assertEqual(specialized_thing.hue_id, specialized_thing_config["hue_id"])
        self.assertEqual(specialized_thing.name, "specialized_thing")
        self.assertEqual(specialized_thing.cmd_topic, specialized_thing_config["cmd_topic"])
        self.assertEqual(specialized_thing.last_will, specialized_thing_config["last_will"])
        self.assertEqual(specialized_thing.min_brightness, specialized_thing_config["min_brightness"])
        self.assertEqual(specialized_thing.retain, specialized_thing_config["retain"])
        self.assertEqual(specialized_thing.state_topic, specialized_thing_config["state_topic"])
