"""
存储模块测试
"""

import unittest
import sys
import os
import tempfile
import shutil
import sqlite3
from contextlib import redirect_stdout
from decimal import Decimal
from io import StringIO
from types import SimpleNamespace

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.storage.storage_manager import StorageManager, SQLiteStorage
from src.services.application_state import FinanceApplicationState
from src.services.transaction_manager import TransactionManager
from src.models.transaction import Transaction, TransactionType
from src.ui.cli import FinanceCLI


class TestStorageManager(unittest.TestCase):
    """存储管理器测试"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "finance_tracker.db")
        self.storage_manager = StorageManager(self.test_file)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_save_and_load_data(self):
        """测试保存和加载数据"""
        manager = TransactionManager()
        
        t = Transaction(
            amount=Decimal("100"),
            transaction_type=TransactionType.INCOME,
            category="测试"
        )
        manager.add(t)
        
        # 保存
        success = self.storage_manager.save_data(manager.to_dict())
        self.assertTrue(success)
        
        # 加载
        loaded_data = self.storage_manager.load_data()
        self.assertIsNotNone(loaded_data)
        
        # 验证
        new_manager = TransactionManager()
        new_manager.from_dict(loaded_data)
        self.assertEqual(new_manager.transaction_count, 1)
    
    def test_has_data(self):
        """测试检查数据存在"""
        self.assertFalse(self.storage_manager.has_data())
        
        manager = TransactionManager()
        t = Transaction(
            amount=Decimal("100"),
            transaction_type=TransactionType.INCOME,
            category="测试"
        )
        manager.add(t)
        
        self.storage_manager.save_data(manager.to_dict())
        self.assertTrue(self.storage_manager.has_data())
    
    def test_clear_storage(self):
        """测试清除存储"""
        manager = TransactionManager()
        t = Transaction(
            amount=Decimal("100"),
            transaction_type=TransactionType.INCOME,
            category="测试"
        )
        manager.add(t)
        
        self.storage_manager.save_data(manager.to_dict())
        self.assertTrue(self.storage_manager.has_data())
        
        self.storage_manager.clear_storage()
        self.assertFalse(self.storage_manager.has_data())


class TestSQLiteStorage(unittest.TestCase):
    """SQLite-specific schema and budget persistence tests."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.database_path = os.path.join(self.test_dir, "finance_tracker.db")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_creates_normalized_tables(self):
        storage = SQLiteStorage(self.database_path)
        storage.save({"transactions": [], "budgets": {}})

        connection = sqlite3.connect(self.database_path)
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        finally:
            connection.close()

        self.assertIn("transactions", tables)
        self.assertIn("monthly_budgets", tables)
        self.assertIn("category_budgets", tables)
        self.assertIn("app_metadata", tables)

    def test_shared_state_preserves_transactions_and_budgets(self):
        cli_state = FinanceApplicationState(self.database_path)
        cli_state.transaction_manager.add(
            Transaction(
                amount=Decimal("5000"),
                transaction_type=TransactionType.INCOME,
                category="Salary",
            )
        )
        cli_state.budget_manager.set_monthly_budget(2026, 10, Decimal("3000"))
        cli_state.budget_manager.set_category_budget(
            "Food", 2026, 10, Decimal("1000")
        )
        self.assertTrue(cli_state.save())

        gui_state = FinanceApplicationState(self.database_path)
        self.assertTrue(gui_state.load())
        gui_state.transaction_manager.add(
            Transaction(
                amount=Decimal("25"),
                transaction_type=TransactionType.EXPENSE,
                category="Food",
            )
        )
        self.assertTrue(gui_state.save())

        reloaded = FinanceApplicationState(self.database_path)
        self.assertTrue(reloaded.load())
        self.assertEqual(reloaded.transaction_manager.transaction_count, 2)
        self.assertEqual(
            reloaded.budget_manager.get_monthly_budget(2026, 10),
            Decimal("3000"),
        )
        category_budget = reloaded.budget_manager.get_category_budget(
            "Food", 2026, 10
        )
        self.assertIsNotNone(category_budget)
        self.assertEqual(category_budget.amount, Decimal("1000"))

    def test_stale_writer_is_rejected(self):
        seed = FinanceApplicationState(self.database_path)
        seed.transaction_manager.add(
            Transaction(Decimal("100"), TransactionType.INCOME, "Salary")
        )
        self.assertTrue(seed.save())

        gui_state = FinanceApplicationState(self.database_path)
        cli_state = FinanceApplicationState(self.database_path)
        self.assertTrue(gui_state.load())
        self.assertTrue(cli_state.load())

        gui_state.transaction_manager.add(
            Transaction(Decimal("20"), TransactionType.EXPENSE, "Food")
        )
        self.assertTrue(gui_state.save())

        cli_state.transaction_manager.add(
            Transaction(Decimal("30"), TransactionType.EXPENSE, "Traffic")
        )
        self.assertFalse(cli_state.save())
        self.assertIn("another process", cli_state.last_error)

        latest = FinanceApplicationState(self.database_path)
        self.assertTrue(latest.load())
        self.assertEqual(latest.transaction_manager.transaction_count, 2)

    def test_cli_reloads_latest_state_after_stale_save(self):
        seed = FinanceApplicationState(self.database_path)
        seed.transaction_manager.add(
            Transaction(Decimal("100"), TransactionType.INCOME, "Salary")
        )
        self.assertTrue(seed.save())

        cli_state = FinanceApplicationState(self.database_path)
        cli = FinanceCLI(
            config=SimpleNamespace(quiet=True),
            state=cli_state,
        )

        other_state = FinanceApplicationState(self.database_path)
        self.assertTrue(other_state.load())
        other_state.transaction_manager.add(
            Transaction(Decimal("20"), TransactionType.EXPENSE, "Food")
        )
        self.assertTrue(other_state.save())

        cli_state.transaction_manager.add(
            Transaction(Decimal("30"), TransactionType.EXPENSE, "Traffic")
        )
        with redirect_stdout(StringIO()):
            self.assertFalse(cli._save_data())

        self.assertEqual(cli_state.transaction_manager.transaction_count, 2)
        self.assertEqual(
            {item.category for item in cli_state.transaction_manager.find_all()},
            {"Salary", "Food"},
        )

class TestPersistenceScenario(unittest.TestCase):
    """持久化场景测试"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "finance_tracker.db")
    
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_full_persistence_cycle(self):
        """完整持久化周期测试"""
        # 第一次运行 - 添加数据
        manager1 = TransactionManager()
        
        t1 = Transaction(
            amount=Decimal("5000"),
            transaction_type=TransactionType.INCOME,
            category="工资"
        )
        t2 = Transaction(
            amount=Decimal("1000"),
            transaction_type=TransactionType.EXPENSE,
            category="房租"
        )
        
        manager1.add(t1)
        manager1.add(t2)
        
        storage = StorageManager(self.test_file)
        storage.save_data(manager1.to_dict())
        
        # 第二次运行 - 加载数据
        manager2 = TransactionManager()
        loaded_data = storage.load_data()
        manager2.from_dict(loaded_data)
        
        self.assertEqual(manager2.transaction_count, 2)
        self.assertEqual(manager2.get_total_income(), Decimal("5000"))
        self.assertEqual(manager2.get_total_expense(), Decimal("1000"))
        
        # 添加新记录
        t3 = Transaction(
            amount=Decimal("200"),
            transaction_type=TransactionType.EXPENSE,
            category="餐饮"
        )
        manager2.add(t3)
        
        # 模拟退出后再次加载
        storage.save_data(manager2.to_dict())
        
        manager3 = TransactionManager()
        loaded_data2 = storage.load_data()
        manager3.from_dict(loaded_data2)
        
        self.assertEqual(manager3.transaction_count, 3)


if __name__ == '__main__':
    unittest.main()
