

class HueBridgeDefaults:

    GROUP_DEBOUNCE_TIME = 300  # milliseconds


class HueBridgeConfKey:

    HOST = "host"
    APP_KEY = "app_key"
    GROUP_DEBOUNCE_TIME = "group_debounce_time"


HUE_BRIDGE_JSONSCHEMA = {
    "additionalProperties": False,
    "required": [HueBridgeConfKey.HOST, HueBridgeConfKey.APP_KEY],
    "type": "object",
    "properties": {
        HueBridgeConfKey.HOST: {"type": "string", "minLength": 1, "description": "Host name or IP address"},
        HueBridgeConfKey.APP_KEY: {"type": "string", "minLength": 1, "description": "App key"},
        HueBridgeConfKey.GROUP_DEBOUNCE_TIME: {
            "type": "number",
            "minimum": 1,
            "maximum": 1000,
            "description": "Hue child lights trigger a group message after this time, Default is "
                           f"{HueBridgeDefaults.GROUP_DEBOUNCE_TIME} milliseconds"
        }
    },
}
