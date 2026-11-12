"""SQLite persistence for the finance tracker."""

import os
import sqlite3
from abc import ABC, abstractmethod
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from ..core.paths import get_database_path
from ..exceptions.custom_exceptions import StorageError


class StorageBackend(ABC):
    """Abstract persistence backend."""

    @abstractmethod
    def save(self, data: dict) -> None:
        pass

    @abstractmethod
    def load(self) -> Optional[dict]:
        pass

    @abstractmethod
    def exists(self) -> bool:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    @abstractmethod
    def get_metadata(self) -> dict:
        pass


class SQLiteStorage(StorageBackend):
    """Transactional SQLite storage shared by the GUI and CLI."""

    SCHEMA_VERSION = "2"

    def __init__(self, filepath: str, timeout: float = 10.0):
        self._filepath = str(Path(filepath).expanduser().resolve())
        self._timeout = timeout
        self._revision = 0
        Path(self._filepath).parent.mkdir(parents=True, exist_ok=True)

    @property
    def revision(self) -> int:
        return self._revision

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._filepath, timeout=self._timeout)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            connection.execute("PRAGMA journal_mode = WAL")
            self._ensure_schema(connection)
        except Exception:
            connection.close()
            raise
        return connection

    def _ensure_schema(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                position INTEGER NOT NULL,
                amount TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                account TEXT NOT NULL,
                transaction_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                author_id TEXT NOT NULL DEFAULT '',
                author_name TEXT NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_date
                ON transactions(transaction_date);
            CREATE INDEX IF NOT EXISTS idx_transactions_category
                ON transactions(category);
            CREATE INDEX IF NOT EXISTS idx_transactions_type
                ON transactions(transaction_type);

            CREATE TABLE IF NOT EXISTS monthly_budgets (
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                amount TEXT NOT NULL,
                PRIMARY KEY (year, month)
            );

            CREATE TABLE IF NOT EXISTS category_budgets (
                category TEXT NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                amount TEXT NOT NULL,
                spent TEXT NOT NULL,
                PRIMARY KEY (category, year, month)
            );
            """
        )
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT OR IGNORE INTO app_metadata(key, value) VALUES('schema_version', ?)",
            (self.SCHEMA_VERSION,),
        )
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(transactions)")}
        for column in ("author_id", "author_name"):
            if column not in columns:
                connection.execute(f"ALTER TABLE transactions ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
        connection.execute("UPDATE app_metadata SET value = ? WHERE key = 'schema_version'", (self.SCHEMA_VERSION,))
        connection.execute(
            "INSERT OR IGNORE INTO app_metadata(key, value) VALUES('revision', '0')"
        )
        connection.execute(
            "INSERT OR IGNORE INTO app_metadata(key, value) VALUES('budget_alert_threshold', '80.0')"
        )
        connection.commit()

    @staticmethod
    def _metadata_value(connection: sqlite3.Connection, key: str, default: str) -> str:
        row = connection.execute(
            "SELECT value FROM app_metadata WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def save(self, data: dict) -> None:
        if not isinstance(data, dict):
            raise StorageError("save", "Application data must be a dictionary")

        connection: Optional[sqlite3.Connection] = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")

            current_revision = int(
                self._metadata_value(connection, "revision", "0")
            )
            expected_revision = data.get("_storage_revision")
            if (
                expected_revision is not None
                and int(expected_revision) != current_revision
            ):
                raise StorageError(
                    "save",
                    "The ledger was changed by another process. Reload it before saving.",
                )

            connection.execute("DELETE FROM transactions")
            transaction_rows = []
            for position, transaction in enumerate(data.get("transactions", [])):
                transaction_rows.append(
                    (
                        transaction["transaction_id"],
                        position,
                        str(transaction["amount"]),
                        transaction["transaction_type"],
                        transaction["category"],
                        transaction.get("description", ""),
                        transaction.get("account", "Default account"),
                        transaction["transaction_date"],
                        transaction["created_at"],
                        transaction.get("author_id", ""),
                        transaction.get("author_name", ""),
                    )
                )
            connection.executemany(
                """
                INSERT INTO transactions(
                    transaction_id, position, amount, transaction_type,
                    category, description, account, transaction_date, created_at,
                    author_id, author_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                transaction_rows,
            )

            if "budgets" in data:
                budgets = data.get("budgets") or {}
                connection.execute("DELETE FROM monthly_budgets")
                connection.execute("DELETE FROM category_budgets")

                monthly_rows = []
                for key, amount in budgets.get("monthly_budgets", {}).items():
                    year, month = (int(value) for value in key.split("-", 1))
                    monthly_rows.append((year, month, str(amount)))
                connection.executemany(
                    "INSERT INTO monthly_budgets(year, month, amount) VALUES (?, ?, ?)",
                    monthly_rows,
                )

                category_rows = [
                    (
                        budget["category"],
                        int(budget["year"]),
                        int(budget["month"]),
                        str(budget["amount"]),
                        str(budget.get("spent", "0")),
                    )
                    for budget in budgets.get("category_budgets", [])
                ]
                connection.executemany(
                    """
                    INSERT INTO category_budgets(
                        category, year, month, amount, spent
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    category_rows,
                )
                connection.execute(
                    """
                    INSERT INTO app_metadata(key, value)
                    VALUES('budget_alert_threshold', ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (str(budgets.get("alert_threshold", 80.0)),),
                )

            new_revision = current_revision + 1
            now = datetime.now().isoformat()
            connection.execute(
                "UPDATE app_metadata SET value = ? WHERE key = 'revision'",
                (str(new_revision),),
            )
            connection.execute(
                """
                INSERT INTO app_metadata(key, value)
                VALUES('last_modified', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (now,),
            )
            connection.commit()
            self._revision = new_revision
        except StorageError:
            if connection is not None:
                connection.rollback()
            raise
        except (sqlite3.Error, KeyError, TypeError, ValueError) as error:
            if connection is not None:
                connection.rollback()
            raise StorageError("save", f"Unable to save SQLite data: {error}")
        finally:
            if connection is not None:
                connection.close()

    def load(self) -> Optional[dict]:
        if not self.exists():
            return None

        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN")
                transactions = [
                    {
                        "transaction_id": row["transaction_id"],
                        "amount": row["amount"],
                        "transaction_type": row["transaction_type"],
                        "category": row["category"],
                        "description": row["description"],
                        "account": row["account"],
                        "transaction_date": row["transaction_date"],
                        "created_at": row["created_at"],
                        "author_id": row["author_id"],
                        "author_name": row["author_name"],
                    }
                    for row in connection.execute(
                        "SELECT * FROM transactions ORDER BY position"
                    )
                ]

                zero = Decimal("0")
                total_income = sum(
                    (
                        Decimal(item["amount"])
                        for item in transactions
                        if item["transaction_type"] == "INCOME"
                    ),
                    zero,
                )
                total_expense = sum(
                    (
                        Decimal(item["amount"])
                        for item in transactions
                        if item["transaction_type"] == "EXPENSE"
                    ),
                    zero,
                )

                monthly_budgets = {
                    f"{row['year']}-{row['month']}": row["amount"]
                    for row in connection.execute(
                        "SELECT year, month, amount FROM monthly_budgets"
                    )
                }
                category_budgets = [
                    {
                        "category": row["category"],
                        "year": row["year"],
                        "month": row["month"],
                        "amount": row["amount"],
                        "spent": row["spent"],
                    }
                    for row in connection.execute(
                        """
                        SELECT category, year, month, amount, spent
                        FROM category_budgets
                        ORDER BY year, month, category
                        """
                    )
                ]
                revision = int(self._metadata_value(connection, "revision", "0"))
                threshold = float(
                    self._metadata_value(
                        connection, "budget_alert_threshold", "80.0"
                    )
                )
                self._revision = revision

                return {
                    "transactions": transactions,
                    "statistics": {
                        "total_income": str(total_income),
                        "total_expense": str(total_expense),
                    },
                    "budgets": {
                        "category_budgets": category_budgets,
                        "monthly_budgets": monthly_budgets,
                        "alert_threshold": threshold,
                    },
                    "_storage_revision": revision,
                }
        except (sqlite3.Error, TypeError, ValueError) as error:
            raise StorageError("load", f"Unable to load SQLite data: {error}")

    def exists(self) -> bool:
        return os.path.isfile(self._filepath)

    def clear(self) -> None:
        for suffix in ("", "-wal", "-shm"):
            target = self._filepath + suffix
            if os.path.exists(target):
                try:
                    os.remove(target)
                except OSError as error:
                    raise StorageError("clear", f"Unable to remove {target}: {error}")
        self._revision = 0

    def get_metadata(self) -> dict:
        if not self.exists():
            return {"exists": False, "backend": "sqlite", "path": self._filepath}
        try:
            with closing(self._connect()) as connection:
                transaction_count = connection.execute(
                    "SELECT COUNT(*) AS count FROM transactions"
                ).fetchone()["count"]
                revision = int(self._metadata_value(connection, "revision", "0"))
                last_modified = self._metadata_value(
                    connection, "last_modified", ""
                )
            stat = os.stat(self._filepath)
            return {
                "exists": True,
                "backend": "sqlite",
                "size": stat.st_size,
                "last_modified": last_modified,
                "path": self._filepath,
                "transaction_count": transaction_count,
                "revision": revision,
                "schema_version": self.SCHEMA_VERSION,
            }
        except sqlite3.Error as error:
            raise StorageError("metadata", f"Unable to inspect SQLite data: {error}")


class StorageManager:
    """Application-facing persistence facade backed by SQLite by default."""

    def __init__(
        self,
        storage_path: Optional[str] = None,
        backend: Optional[StorageBackend] = None,
    ):
        path = str(storage_path or get_database_path())
        self._storage: StorageBackend = backend or SQLiteStorage(path)
        self._is_loaded = False
        self._data: Optional[dict] = None
        self._last_error: Optional[str] = None

    @property
    def storage_path(self) -> str:
        return self._storage._filepath

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @property
    def revision(self) -> int:
        return getattr(self._storage, "revision", 0)

    def save_data(self, data: dict) -> bool:
        try:
            self._storage.save(data)
            saved_data = dict(data)
            saved_data["_storage_revision"] = self.revision
            self._data = saved_data
            self._last_error = None
            return True
        except StorageError as error:
            self._last_error = str(error)
            return False

    def load_data(self) -> Optional[dict]:
        try:
            self._data = self._storage.load()
            self._is_loaded = True
            self._last_error = None
            return self._data
        except StorageError as error:
            self._last_error = str(error)
            return None

    def has_data(self) -> bool:
        return self._storage.exists()

    def is_loaded(self) -> bool:
        return self._is_loaded

    def get_metadata(self) -> dict:
        try:
            return self._storage.get_metadata()
        except StorageError as error:
            self._last_error = str(error)
            return {"exists": False, "error": str(error), "path": self.storage_path}

    def clear_storage(self) -> bool:
        try:
            self._storage.clear()
            self._data = None
            self._is_loaded = False
            self._last_error = None
            return True
        except StorageError as error:
            self._last_error = str(error)
            return False

