#!/usr/bin/env python3
import asyncio
import logging
import sys
from typing import Optional, List

import click
from yaml.parser import ParserError

from src.app_config import AppConfig, ConfigException, RunMode
from src.app_logging import AppLogging, LOGGING_CHOICES
from src.device.device import Device
from src.device.device_factory import DeviceFactory
from src.hue.hue_app_key import HueAppKey
from src.hue.hue_connector import HueConnector, HueConnectorBase
from src.hue.hue_explore import HueExplore
from src.mqtt.mqtt_client import MqttClient
from src.mqtt.mqtt_proxy import MqttProxy
from src.runner import Runner

_logger = logging.getLogger("main")


@click.command()
@click.option(
    "--create-app-key",
    is_flag=True,
    help="Creates an app token to connect the Hue bridge."
)
@click.option(
    "--discover",
    is_flag=True,
    help="Find Hue bridges within your network."
)
@click.option(
    "--explore",
    is_flag=True,
    help="List all bridge devices and compare with your configuration."
)
@click.option(
    "--json-schema",
    is_flag=True,
    help="Prints the config file JSON schema and exits. (JSON schema is used to validate the YAML config.)"
)
@click.option(
    "--config-file",
    help="Config file",
)
@click.option(
    "--log-file",
    help="Log file"
)
@click.option(
    "--log-level",
    help="Log level",
    type=click.Choice(LOGGING_CHOICES, case_sensitive=False),
)
@click.option(
    "--print-log-console",
    is_flag=True,
    help="Print log output to console too."
)
@click.option(
    "--skip-log-times",
    is_flag=True,
    help="Skip log timestamp (systemd/journald logs get their own timestamp)."
)
def _main(
    create_app_key, discover, explore, json_schema, config_file, log_file, log_level, print_log_console, skip_log_times
):
    """
    Connect a Philips Hue bridge via MQTT. It's supposed to run as service but offers also some utility functions:
    creating app tokens, discovering Hue bridges, exploring Hue device and comparing with your configuration
    """
    # noinspection SpellCheckingInspection
    config_error_code = 78  # sysexits.h: define EX_CONFIG 78 /* configuration error */

    try:
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(testable_main(
                create_app_key, discover, explore, json_schema, config_file, log_file, log_level, print_log_console, skip_log_times
            ))
        finally:
            loop.close()

    except KeyboardInterrupt:
        pass
    except ConfigException as ex:
        _logger.error(ex)
        sys.exit(config_error_code)
    except ParserError as ex:
        _logger.error("parsing error in config file:\n%s", ex)
        sys.exit(config_error_code)
    except Exception as ex:
        _logger.exception(ex)
        sys.exit(1)  # a simple return is not understood by click


async def testable_main(
    create_app_key, discover, explore, json_schema, config_file, log_file, log_level, print_log_console, skip_log_times
):
    """
    Due to the click annotations, _main cannot be called from within tests
    """
    run_mode = AppConfig.determine_run_mode(create_app_key, discover, explore, json_schema)

    devices: List[Device] = []
    hue_bridge: Optional[HueConnectorBase] = None
    mqtt_client: Optional[MqttClient] = None
    mqtt_proxy: Optional[MqttProxy] = None

    try:
        _logger.debug(run_mode)

        if run_mode != RunMode.JSON_SCHEMA and run_mode != RunMode.DISCOVER:
            app_config = AppConfig(config_file, run_mode)
            AppLogging.configure(
                app_config.get_logging_config(),
                log_file, log_level, print_log_console, skip_log_times,
            )

            if run_mode in [RunMode.RUN_SERVICE, RunMode.EXPLORE]:
                devices = DeviceFactory.create_devices(app_config.get_devices_config(), app_config.get_device_defaults_config())

            if run_mode == RunMode.RUN_SERVICE:
                hue_bridge = HueConnector(app_config.get_hue_bridge_config(), devices)
                mqtt_client = MqttClient(app_config.get_mqtt_config())
                mqtt_proxy = MqttProxy(mqtt_client, devices)
            elif run_mode == RunMode.CREATE_APP_KEY:
                hue_bridge = HueAppKey(app_config.get_hue_bridge_config(), devices)
            elif run_mode == RunMode.EXPLORE:
                hue_bridge = HueExplore(app_config.get_hue_bridge_config(), devices)

        if run_mode == RunMode.JSON_SCHEMA:
            AppConfig.print_config_file_json_schema()
        elif run_mode == RunMode.DISCOVER:
            await HueExplore.discover()
        elif run_mode == RunMode.EXPLORE:
            await hue_bridge.run_tools()  # no loop
        elif run_mode == RunMode.CREATE_APP_KEY:
            await hue_bridge.run_tools()  # no loop
        else:
            runner = Runner(hue_bridge, mqtt_proxy)
            await runner.run()

    finally:
        _logger.info("shutdown")
        if mqtt_proxy is not None:
            await mqtt_proxy.close()
        if hue_bridge is not None:
            await hue_bridge.close()
        if mqtt_client is not None:
            mqtt_client.close()


if __name__ == '__main__':
    _main()  # exit codes must be handled by click!
