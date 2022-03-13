
DEFAULT_TOPIC_KEY_PATTERN = "{THING_KEY}"
_thing_key_info = f"May contain '{DEFAULT_TOPIC_KEY_PATTERN}', which will be replaced with the thing key."


class ThingDefaultConfKey:

    CMD_TOPIC = "cmd_topic"
    LAST_WILL = "last_will"
    MIN_BRIGHTNESS = "min_brightness"
    RETAIN = "retain"
    STATE_TOPIC = "state_topic"


class ThingConfKey:

    CMD_TOPIC = "cmd_topic"
    HUE_ID = "hue_id"
    LAST_WILL = "last_will"
    MIN_BRIGHTNESS = "min_brightness"
    RETAIN = "retain"
    STATE_TOPIC = "state_topic"
    TYPE = "type"


THING_DEFAULTS_JSONSCHEMA = {
    "additionalProperties": False,
    "required": [],
    "type": "object",
    "properties": {
        ThingDefaultConfKey.RETAIN: {"type": "boolean", "description": "Default: True"},
        ThingDefaultConfKey.STATE_TOPIC: {
            "type": "string",
            "minLength": 1,
            "description": "Default MQTT state topic (send to). " + _thing_key_info
        },
        ThingDefaultConfKey.CMD_TOPIC: {
            "type": "string",
            "minLength": 1,
            "description": "Default MQTT command topic (listen to). " + _thing_key_info
        },
        ThingDefaultConfKey.LAST_WILL: {
            "type": "string",
            "minLength": 1,
            "description": "Default MQTT last will"
        },
        ThingDefaultConfKey.MIN_BRIGHTNESS: {
            "type": "number",
            "minimum": 1.0,
            "maximum": 100.0,
            "description": "Default min brightness (%). Lower values lads to switching off."
        },
    },
}


THING_JSONSCHEMA = {
    "additionalProperties": False,
    "required": [ThingConfKey.HUE_ID],
    "type": "object",
    "properties": {
        ThingConfKey.CMD_TOPIC: {"type": "string", "minLength": 1, "description": "MQTT command topic (listen to)"},
        ThingConfKey.STATE_TOPIC: {"type": "string", "minLength": 1, "description": "MQTT state topic (send to)"},

        ThingConfKey.HUE_ID: {"type": "string", "minLength": 1, "description": "Hue ID (UUID)"},

        ThingConfKey.RETAIN: {"type": "boolean"},

        ThingDefaultConfKey.LAST_WILL: {
            "type": "string",
            "minLength": 1,
            "description": "Default MQTT last will"
        },

        ThingConfKey.MIN_BRIGHTNESS: {
            "type": "number",
            "minimum": 1.0,
            "maximum": 100.0,
            "description": "Default min brightness (%). Lower values lads to switching off."
        },
        # DeviceConfKey.TYPE: {"type": "string", "enum": DEVICE_TYPES, "description": "Device type"},
    },
}


THINGS_JSONSCHEMA = {
    "type": "object",
    "additionalProperties": THING_JSONSCHEMA,
    "description": "Dictionary of <thing-name>:<thing-properties>"
}
