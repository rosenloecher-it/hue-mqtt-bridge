

class HueBridgeDefaults:

    GROUP_DEBOUNCE_TIME = 300  # milliseconds
    FULL_RELOAD_TIME = 1800  # seconds


class HueBridgeConfKey:

    HOST = "host"
    APP_KEY = "app_key"
    GROUP_DEBOUNCE_TIME = "group_debounce_time"
    FULL_RELOAD_TIME = "full_reload_time"


HUE_BRIDGE_JSONSCHEMA = {
    "additionalProperties": False,
    "required": [HueBridgeConfKey.HOST, HueBridgeConfKey.APP_KEY],
    "type": "object",
    "properties": {
        HueBridgeConfKey.HOST: {"type": "string", "minLength": 1, "description": "Host name or IP address"},
        HueBridgeConfKey.APP_KEY: {"type": "string", "minLength": 1, "description": "App key"},
        HueBridgeConfKey.FULL_RELOAD_TIME: {
            "type": "number",
            "minimum": 60,
            "maximum": 5000,
            "description": "Reload all from Hue bridge after this time, Default is "
                           f"{HueBridgeDefaults.FULL_RELOAD_TIME} seconds."
        },
        HueBridgeConfKey.GROUP_DEBOUNCE_TIME: {
            "type": "number",
            "minimum": 1,
            "maximum": 5000,
            "description": "Hue child lights trigger a group message after this time, Default is "
                           f"{HueBridgeDefaults.GROUP_DEBOUNCE_TIME} milliseconds."
        },
    },
}
