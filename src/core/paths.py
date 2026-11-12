"""Stable application paths shared by the GUI and CLI entry points."""

import os
from pathlib import Path


DATABASE_FILENAME = "finance_tracker.db"


def get_app_data_directory() -> Path:
    """Return the project-local data directory used by every entry point."""
    explicit_directory = os.environ.get("FINANCE_TRACKER_DATA_DIR")
    if explicit_directory:
        directory = Path(explicit_directory).expanduser().resolve()
    else:
        directory = Path(__file__).resolve().parents[2] / "data"

    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_database_path() -> Path:
    """Return the shared SQLite database path, with an override for tests/tools."""
    explicit_path = os.environ.get("FINANCE_TRACKER_DB_PATH")
    if explicit_path:
        path = Path(explicit_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return get_app_data_directory() / DATABASE_FILENAME



