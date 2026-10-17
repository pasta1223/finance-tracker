"""
财务跟踪系统主模块
"""

from .version import APP_VERSION, __version__

__author__ = "Finance Tracker Team"

from .models.transaction import Transaction, TransactionType
from .models.category import Category
from .services.transaction_manager import TransactionManager
from .services.application_state import FinanceApplicationState
from .storage.storage_manager import StorageManager
from .ui.cli import FinanceCLI
from .data_structures import (
    DoublyLinkedList, Stack, Queue,
    BinarySearchTree, HashTable, GeneralTree
)

__all__ = [
    'APP_VERSION', '__version__',
    'Transaction', 'TransactionType',
    'Category',
    'TransactionManager', 'FinanceApplicationState',
    'StorageManager',
    'FinanceCLI',
    'DoublyLinkedList', 'Stack', 'Queue',
    'BinarySearchTree', 'HashTable', 'GeneralTree'
]
