"""Regression tests for command-line startup options."""

import unittest
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from main import main
from src.core.arguments import ArgumentParser
from src.core.logger import LogLevel


class TestCLIStartup(unittest.TestCase):
    def test_internal_cli_file_delegates_to_main_entry_point(self):
        project_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(project_root / "src" / "ui" / "cli.py"), "--version"],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("finance-tracker v1.2.0", result.stdout)

    def test_stat_argument_is_preserved(self):
        args = ArgumentParser().parse(["--stat"])
        self.assertTrue(args.stat)

    @patch("main.run_command_mode", return_value=0)
    @patch("main.FinanceCLI")
    @patch("main.init_logger")
    @patch("main.ConfigManager")
    @patch("main.ArgumentParser")
    def test_quiet_uses_warning_without_persisting_config(
        self,
        parser_class,
        config_class,
        init_logger_mock,
        cli_class,
        run_command_mode_mock,
    ):
        args = SimpleNamespace(
            version=False,
            show_config=False,
            reset_config=False,
            quiet=True,
            debug=False,
            add_transaction=False,
            list_transactions=True,
            search=None,
            export=None,
            stat=False,
            start_date=None,
            end_date=None,
            category=None,
            transaction_type=None,
        )
        parser_class.return_value.parse.return_value = args
        config = MagicMock()
        config_class.return_value = config
        logger = Mock()
        init_logger_mock.return_value = logger
        app = Mock()
        cli_class.return_value = app

        self.assertEqual(main(), 0)

        logger.set_level.assert_called_once_with(LogLevel.WARNING)
        config.__setitem__.assert_not_called()
        cli_class.assert_called_once_with(
            config=config,
            logger=logger,
            quiet=True,
        )
        run_command_mode_mock.assert_called_once_with(app, args, logger)


if __name__ == "__main__":
    unittest.main()
