
class HueBridgeConfKey:

    HOST = "host"
    APP_KEY = "app_key"


HUE_BRIDGE_JSONSCHEMA = {
    "additionalProperties": False,
    "required": [HueBridgeConfKey.HOST, HueBridgeConfKey.APP_KEY],
    "type": "object",
    "properties": {
        HueBridgeConfKey.HOST: {"type": "string", "minLength": 1, "description": "Host name or IP address"},
        HueBridgeConfKey.APP_KEY: {"type": "string", "minLength": 1, "description": "App key"},
    },
}
