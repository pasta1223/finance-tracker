"""Application configuration persisted in the shared SQLite database."""

import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, Optional

from .paths import get_database_path
from ..version import APP_VERSION


@dataclass
class AppConfig:
    """Typed application configuration."""

    app_name: str = "个人财务跟踪系统"
    app_version: str = APP_VERSION

    auto_save: bool = True

    log_enabled: bool = True
    log_file: str = "data/app.log"
    log_level: str = "INFO"

    currency_symbol: str = "¥"
    date_format: str = "%Y-%m-%d"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    decimal_places: int = 2

    monthly_budget: float = 0.0
    budget_alert_threshold: float = 0.8

    income_categories: list = field(
        default_factory=lambda: ["工资", "奖金", "投资收益", "兼职", "其他收入"]
    )
    expense_categories: list = field(
        default_factory=lambda: [
            "餐饮", "交通", "购物", "住房", "医疗",
            "教育", "娱乐", "通讯", "其他支出",
        ]
    )
    default_account: str = "默认账户"
    accounts: list = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Create a configuration while ignoring obsolete database keys."""
        valid_names = {item.name for item in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in valid_names})


class ConfigManager:
    """Load and save configuration rows in the shared SQLite database."""

    LIST_SEPARATOR = "\x1f"

    def __init__(self, database_path: Optional[str] = None):
        self._database_path = str(
            Path(database_path or get_database_path()).expanduser().resolve()
        )
        Path(self._database_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()
        self._config = self._load_config()

    @property
    def database_path(self) -> str:
        return self._database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _ensure_schema(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS app_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    value_type TEXT NOT NULL
                )
                """
            )

    @classmethod
    def _encode_value(cls, value: Any) -> tuple[str, str]:
        if isinstance(value, bool):
            return ("1" if value else "0", "bool")
        if isinstance(value, int):
            return (str(value), "int")
        if isinstance(value, float):
            return (repr(value), "float")
        if isinstance(value, list):
            return (cls.LIST_SEPARATOR.join(str(item) for item in value), "list")
        return (str(value), "str")

    @classmethod
    def _decode_value(cls, value: str, value_type: str) -> Any:
        if value_type == "bool":
            return value == "1"
        if value_type == "int":
            return int(value)
        if value_type == "float":
            return float(value)
        if value_type == "list":
            return [] if value == "" else value.split(cls.LIST_SEPARATOR)
        return value

    def _load_config(self) -> AppConfig:
        defaults = AppConfig().to_dict()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT key, value, value_type FROM app_config"
            ).fetchall()

        if not rows:
            config = AppConfig()
            self._save_config(config)
            return config

        stored = {
            row["key"]: self._decode_value(row["value"], row["value_type"])
            for row in rows
        }
        defaults.update(stored)
        # The application version describes the installed code, not a user
        # preference. Upgrade stale values left by earlier releases.
        defaults["app_version"] = APP_VERSION
        config = AppConfig.from_dict(defaults)

        # Add defaults introduced by newer versions without overwriting user values.
        self._save_config(config)
        return config

    def _save_config(self, config: Optional[AppConfig] = None) -> None:
        current = config or self._config
        rows = [
            (key, *self._encode_value(value))
            for key, value in current.to_dict().items()
        ]
        with closing(self._connect()) as connection, connection:
            connection.executemany(
                """
                INSERT INTO app_config(key, value, value_type)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    value_type = excluded.value_type
                """,
                rows,
            )

    def save(self) -> None:
        self._save_config()

    @property
    def config(self) -> AppConfig:
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self._config, key, default)

    def set(self, key: str, value: Any) -> None:
        if not hasattr(self._config, key):
            raise ValueError(f"无效的配置项: {key}")
        setattr(self._config, key, value)
        self.save()

    def reset_to_default(self) -> None:
        self._config = AppConfig()
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM app_config")
        self.save()

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)
