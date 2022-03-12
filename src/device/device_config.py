
class DeviceType:
    COLOR = "color"
    DIMMER = "dimmer"
    MOTION_SENSOR = "motion_sensor"
    SWITCH = "switch"


DEFAULT_TOPIC_KEY_PATTERN = "{DEVICE_KEY}"
_device_key_info = f"May contain '{DEFAULT_TOPIC_KEY_PATTERN}', which will be replaced with the device key."


class DeviceDefaultConfKey:

    CMD_TOPIC = "cmd_topic"
    LAST_WILL = "last_will"
    MIN_BRIGHTNESS = "min_brightness"
    RETAIN = "retain"
    STATE_TOPIC = "state_topic"


class DeviceConfKey:

    CMD_TOPIC = "cmd_topic"
    HUE_ID = "hue_id"
    MIN_BRIGHTNESS = "min_brightness"
    RETAIN = "retain"
    STATE_TOPIC = "state_topic"
    TYPE = "type"


DEVICE_DEFAULTS_JSONSCHEMA = {
    "additionalProperties": False,
    "required": [],
    "type": "object",
    "properties": {
        DeviceDefaultConfKey.RETAIN: {"type": "boolean", "description": "Default: True"},
        DeviceDefaultConfKey.STATE_TOPIC: {
            "type": "string",
            "minLength": 1,
            "description": "Default MQTT state topic (send to). " + _device_key_info
        },
        DeviceDefaultConfKey.CMD_TOPIC: {
            "type": "string",
            "minLength": 1,
            "description": "Default MQTT command topic (listen to). " + _device_key_info
        },
        DeviceDefaultConfKey.LAST_WILL: {
            "type": "string",
            "minLength": 1,
            "description": "Default MQTT last will"
        },
        DeviceDefaultConfKey.MIN_BRIGHTNESS: {
            "type": "number",
            "minimum": 1.0,
            "maximum": 100.0,
            "description": "Default min brightness (%). Lower values lads to switching off."
        },
    },
}


DEVICE_JSONSCHEMA = {
    "additionalProperties": False,
    "required": [DeviceConfKey.HUE_ID],
    "type": "object",
    "properties": {
        DeviceConfKey.CMD_TOPIC: {"type": "string", "minLength": 1, "description": "MQTT command topic (listen to)"},
        DeviceConfKey.STATE_TOPIC: {"type": "string", "minLength": 1, "description": "MQTT state topic (send to)"},

        DeviceConfKey.HUE_ID: {"type": "string", "minLength": 1, "description": "Hue ID (UUID)"},

        DeviceConfKey.RETAIN: {"type": "boolean"},

        DeviceConfKey.MIN_BRIGHTNESS: {
            "type": "number",
            "minimum": 1.0,
            "maximum": 100.0,
            "description": "Default min brightness (%). Lower values lads to switching off."
        },
        # DeviceConfKey.TYPE: {"type": "string", "enum": DEVICE_TYPES, "description": "Device type"},
    },
}


DEVICES_JSONSCHEMA = {
    "type": "object",
    "additionalProperties": DEVICE_JSONSCHEMA,
    "description": "Dictionary of <device-name>:<device-properties>"
}
