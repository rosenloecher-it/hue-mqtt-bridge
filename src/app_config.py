import copy
import json
import os
from enum import Enum

import yaml
from jsonschema import validate

from src.app_logging import LOGGING_JSONSCHEMA
from src.thing.thing_config import THINGS_JSONSCHEMA, THING_DEFAULTS_JSONSCHEMA
from src.hue.hue_config import HUE_BRIDGE_JSONSCHEMA
from src.mqtt.mqtt_config import MQTT_JSONSCHEMA


class ConfigException(Exception):
    pass


class RunMode(Enum):
    CREATE_APP_KEY = "create app key"
    DISCOVER = "discover Hue bridges"
    EXPLORE = "explore bridge devices"
    JSON_SCHEMA = "show JSON schema"
    RUN_SERVICE = "start service"


class AppConfKey:
    HUE_BRIDGE = "hue_bridge"
    LOGGING = "logging"
    MQTT = "mqtt"
    THINGS = "things"
    THING_DEFAULTS = "thing_defaults"
    YAML_TEMPLATES = "yaml_templates"


CONFIG_JSONSCHEMA = {
    "type": "object",
    "properties": {
        AppConfKey.THINGS: THINGS_JSONSCHEMA,
        AppConfKey.THING_DEFAULTS: THING_DEFAULTS_JSONSCHEMA,
        AppConfKey.HUE_BRIDGE: HUE_BRIDGE_JSONSCHEMA,
        AppConfKey.LOGGING: LOGGING_JSONSCHEMA,
        AppConfKey.MQTT: MQTT_JSONSCHEMA,

        AppConfKey.YAML_TEMPLATES: {
            "type": "object",
            "additionalProperties": True,
            "description":
                "The strict schema prevents putting objects anywhere outside of given structure. This constrains the YAML reference "
                "feature. Therefore this section is supposed to contain arbitrary objects without a schema validation. Also nothing "
                "within this section is used by worker-bunch directly. So put your reusable YAML referenced objects here."
        },
    },
    "additionalProperties": False,
    "required": [AppConfKey.THINGS, AppConfKey.HUE_BRIDGE, AppConfKey.MQTT],
}


class AppConfig:

    def __init__(self, config_file, run_mode):
        self._config_data = {}

        self.check_config_file_access(config_file)

        with open(config_file, 'r') as stream:
            file_data = yaml.unsafe_load(stream)

        self._config_data = {
            **{"database": {}, "logging": {}, "mqtt": {}},  # default
            **file_data
        }

        schema = CONFIG_JSONSCHEMA
        if run_mode == RunMode.EXPLORE:
            schema = copy.deepcopy(schema)
            schema["properties"][AppConfKey.MQTT] = {"type": "object"}
            schema["required"].remove(AppConfKey.MQTT)

        validate(file_data, schema)

    def get_things_config(self):
        return self._config_data[AppConfKey.THINGS]

    def get_thing_defaults_config(self):
        return self._config_data.get(AppConfKey.THING_DEFAULTS, {})

    def get_hue_bridge_config(self):
        return self._config_data[AppConfKey.HUE_BRIDGE]

    def get_logging_config(self):
        return self._config_data.get(AppConfKey.LOGGING, {})

    def get_mqtt_config(self):
        return self._config_data[AppConfKey.MQTT]

    @classmethod
    def determine_run_mode(cls, create_app_key, discover, explore, json_schema) -> RunMode:
        special_command_count = (1 if json_schema else 0) + (1 if discover else 0) + (1 if explore else 0) + (1 if create_app_key else 0)
        if special_command_count > 1:
            raise ConfigException("Use only one special mode command (create-user, discover, explore, json-schema)!")

        if create_app_key:
            return RunMode.CREATE_APP_KEY
        if discover:
            return RunMode.DISCOVER
        if explore:
            return RunMode.EXPLORE
        if json_schema:
            return RunMode.JSON_SCHEMA

        return RunMode.RUN_SERVICE

    @classmethod
    def check_config_file_access(cls, config_file):
        if not os.path.isfile(config_file):
            raise FileNotFoundError('config file ({}) does not exist!'.format(config_file))

        permissions = oct(os.stat(config_file).st_mode & 0o777)[2:]
        if permissions != "600":
            extra = "change via 'chmod'. this config file may contain sensitive information."
            raise PermissionError(f"wrong config file permissions ({config_file}: expected 600, got {permissions})! {extra}")

    @classmethod
    def print_config_file_json_schema(cls):
        print(json.dumps(CONFIG_JSONSCHEMA, indent=4, sort_keys=True))
