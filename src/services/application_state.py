"""Shared application state and persistence workflow for every user interface."""

from typing import Optional

from ..core.paths import get_database_path
from ..storage.storage_manager import StorageManager
from .budget_manager import BudgetManager
from .transaction_manager import TransactionManager


class FinanceApplicationState:
    """Own transactions, budgets, and their shared SQLite persistence lifecycle."""

    SCHEMA_VERSION = 2

    def __init__(
        self,
        database_path: Optional[str] = None,
    ):
        self.storage = StorageManager(str(database_path or get_database_path()))
        self.transaction_manager = TransactionManager()
        self.budget_manager = BudgetManager()
        self._storage_revision = 0

    @property
    def storage_path(self) -> str:
        return self.storage.storage_path

    @property
    def last_error(self) -> Optional[str]:
        return self.storage.last_error

    def load(self) -> bool:
        """Load the complete state from SQLite."""
        data = self.storage.load_data()
        if data is None:
            return False

        self._apply_data(data)
        return True

    def save(self) -> bool:
        """Save transactions and budgets together through the shared SQLite store."""
        data = self.to_dict()
        data["_storage_revision"] = self._storage_revision
        if not self.storage.save_data(data):
            return False
        self._storage_revision = self.storage.revision
        return True

    def reload(self) -> bool:
        """Discard in-memory state and reload the latest committed database state."""
        return self.load()

    def to_dict(self) -> dict:
        data = self.transaction_manager.to_dict()
        data["schema_version"] = self.SCHEMA_VERSION
        data["budgets"] = self.budget_manager.to_dict()
        return data

    def _apply_data(self, data: dict) -> None:
        self.transaction_manager.from_dict(data)
        self.budget_manager.from_dict(data.get("budgets", {}))
        self._storage_revision = int(data.get("_storage_revision", 0))

