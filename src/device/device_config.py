
class DeviceType:
    COLOR = "color"
    DIMMER = "dimmer"
    MOTION_SENSOR = "motion_sensor"
    SWITCH = "switch"


DEFAULT_TOPIC_KEY_PATTERN = "{DEVICE_KEY}"
_device_key_info = f"May contain '{DEFAULT_TOPIC_KEY_PATTERN}', which will be replaced with the device key."


class DeviceDefaultConfKey:

    RETAIN = "retain"
    STATE_TOPIC = "state_topic"
    CMD_TOPIC = "cmd_topic"
    LAST_WILL = "last_will"


class DeviceConfKey:

    CMD_TOPIC = "cmd_topic"
    STATE_TOPIC = "state_topic"
    RETAIN = "retain"
    HUE_ID = "hue_id"
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

        # DeviceConfKey.TYPE: {"type": "string", "enum": DEVICE_TYPES, "description": "Device type"},
    },
}


DEVICES_JSONSCHEMA = {
    "type": "object",
    "additionalProperties": DEVICE_JSONSCHEMA,
    "description": "Dictionary of <device-name>:<device-properties>"
}
