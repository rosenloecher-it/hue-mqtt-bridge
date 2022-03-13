import unittest

from src.app_config import AppConfig, RunMode, ConfigException


class TestAppConfig(unittest.TestCase):

    def test_determine_run_mode(self):
        self.assertEqual(
            AppConfig.determine_run_mode(False, False, False, False),
            RunMode.RUN_SERVICE
        )

        self.assertEqual(
            AppConfig.determine_run_mode(True, False, False, False),
            RunMode.CREATE_APP_KEY
        )
        self.assertEqual(
            AppConfig.determine_run_mode(False, True, False, False),
            RunMode.DISCOVER
        )
        self.assertEqual(
            AppConfig.determine_run_mode(False, False, True, False),
            RunMode.EXPLORE
        )
        self.assertEqual(
            AppConfig.determine_run_mode(False, False, False, True),
            RunMode.JSON_SCHEMA
        )

        with self.assertRaises(ConfigException):
            AppConfig.determine_run_mode(True, False, False, True),

        with self.assertRaises(ConfigException):
            AppConfig.determine_run_mode(False, True, True, False),
