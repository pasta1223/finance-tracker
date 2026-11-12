"""Shared application state and persistence workflow for every user interface."""

from typing import Optional
from pathlib import Path

from ..core.paths import get_database_path
from ..storage.storage_manager import StorageManager
from .budget_manager import BudgetManager
from .transaction_manager import TransactionManager


class FinanceApplicationState:
    """Own transactions, budgets, and their shared SQLite persistence lifecycle."""

    SCHEMA_VERSION = 3

    def __init__(
        self,
        database_path: Optional[str] = None,
        *, auth_service=None, session=None,
    ):
        self.auth_service = auth_service
        self.session = session
        self._authors = {}
        self._baseline = {}
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
        self._authorize()
        data = self.storage.load_data()
        if data is None:
            return False

        self._apply_data(data)
        return True

    def save(self) -> bool:
        """Save transactions and budgets together through the shared SQLite store."""
        self._authorize()
        if self.session:
            if self.session.kind == "family" and self.session.role != "owner":
                from .auth_service import AuthenticationError
                current = {t.transaction_id: t.to_dict() for t in self.transaction_manager.find_all()}
                for key, original in self._baseline.items():
                    if original.get("author_id") != self.session.member_id and current.get(key) != original:
                        self.reload()
                        raise AuthenticationError("家庭成员只能修改或删除自己添加的记录。")
            for transaction in self.transaction_manager.find_all():
                author = self._authors.get(transaction.transaction_id)
                if author is None:
                    author = (self.session.member_id, self.session.display_name)
                transaction._author_id, transaction._author_name = author
        data = self.to_dict()
        data["_storage_revision"] = self._storage_revision
        if not self.storage.save_data(data):
            return False
        self._storage_revision = self.storage.revision
        self._remember_authors()
        self._baseline = {t.transaction_id: t.to_dict() for t in self.transaction_manager.find_all()}
        return True

    def _authorize(self):
        if self.session:
            from .auth_service import AuthenticationError
            if Path(self.storage_path) != self.auth_service.ledger_path(self.session):
                raise AuthenticationError("当前登录账号与账本不匹配。")

    def _remember_authors(self):
        self._authors.update({t.transaction_id: (t.author_id, t.author_name)
                              for t in self.transaction_manager.find_all()})

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
        self._authors = {}
        self._remember_authors()
        self._baseline = {t.transaction_id: t.to_dict() for t in self.transaction_manager.find_all()}

