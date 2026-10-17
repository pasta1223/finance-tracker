"""
事务管理器集成测试
"""

import unittest
import sys
import os
from datetime import datetime
from decimal import Decimal

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.services.transaction_manager import TransactionManager
from src.models.transaction import Transaction, TransactionType
from src.exceptions.custom_exceptions import NotFoundError


class TestTransactionManager(unittest.TestCase):
    """事务管理器测试"""
    
    def setUp(self):
        self.manager = TransactionManager()
        self._create_sample_transactions()
    
    def _create_sample_transactions(self):
        """创建示例交易"""
        self.t1 = Transaction(
            amount=Decimal("5000"),
            transaction_type=TransactionType.INCOME,
            category="工资",
            description="月薪"
        )
        self.t2 = Transaction(
            amount=Decimal("200"),
            transaction_type=TransactionType.EXPENSE,
            category="餐饮",
            description="午餐"
        )
        self.t3 = Transaction(
            amount=Decimal("1500"),
            transaction_type=TransactionType.EXPENSE,
            category="住房",
            description="房租"
        )
        self.manager.add(self.t1)
        self.manager.add(self.t2)
        self.manager.add(self.t3)
    
    def test_add_transaction(self):
        """测试添加交易"""
        new_t = Transaction(
            amount=Decimal("100"),
            transaction_type=TransactionType.EXPENSE,
            category="购物"
        )
        self.manager.add(new_t)
        self.assertEqual(self.manager.transaction_count, 4)
    
    def test_remove_transaction(self):
        """测试删除交易"""
        initial_count = self.manager.transaction_count
        self.manager.remove(self.t2.transaction_id)
        self.assertEqual(self.manager.transaction_count, initial_count - 1)
    
    def test_find_by_id(self):
        """测试按ID查找 - O(1)"""
        found = self.manager.find_by_id(self.t1.transaction_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.amount, self.t1.amount)
    
    def test_find_by_category(self):
        """测试按分类查找"""
        results = self.manager.find_by_category("餐饮")
        self.assertEqual(len(results), 1)
    
    def test_find_by_type(self):
        """测试按类型查找"""
        incomes = self.manager.find_by_type(TransactionType.INCOME)
        expenses = self.manager.find_by_type(TransactionType.EXPENSE)
        self.assertEqual(len(incomes), 1)
        self.assertEqual(len(expenses), 2)
    
    def test_statistics(self):
        """测试统计功能"""
        income = self.manager.get_total_income()
        expense = self.manager.get_total_expense()
        balance = self.manager.get_balance()
        self.assertEqual(income, Decimal("5000"))
        self.assertEqual(expense, Decimal("1700"))
        self.assertEqual(balance, Decimal("3300"))
    
    def test_undo(self):
        """测试撤销"""
        initial_count = self.manager.transaction_count
        new_t = Transaction(
            amount=Decimal("100"),
            transaction_type=TransactionType.EXPENSE,
            category="测试"
        )
        self.manager.add(new_t)
        self.assertEqual(self.manager.transaction_count, initial_count + 1)
        self.manager.undo()
        self.assertEqual(self.manager.transaction_count, initial_count)
    
    def test_redo(self):
        """测试重做"""
        new_t = Transaction(
            amount=Decimal("100"),
            transaction_type=TransactionType.EXPENSE,
            category="测试"
        )
        self.manager.add(new_t)
        self.manager.undo()
        self.assertTrue(self.manager.can_redo())
        self.manager.redo()
        self.assertIsNotNone(self.manager.find_by_id(new_t.transaction_id))
    
    def test_serialization(self):
        """测试序列化"""
        data = self.manager.to_dict()
        self.assertIn("transactions", data)
        self.assertEqual(len(data["transactions"]), 3)
    
    def test_deserialization(self):
        """测试反序列化"""
        data = self.manager.to_dict()
        new_manager = TransactionManager()
        new_manager.from_dict(data)
        self.assertEqual(new_manager.transaction_count, 3)


class TestEmptyManager(unittest.TestCase):
    """空管理器测试"""
    
    def setUp(self):
        self.manager = TransactionManager()
    
    def test_empty_operations(self):
        """测试空管理器操作"""
        self.assertTrue(self.manager.is_empty)
        self.assertEqual(self.manager.transaction_count, 0)
        self.assertEqual(len(self.manager), 0)
    
    def test_empty_search(self):
        """测试空搜索"""
        results = self.manager.find_by_category("餐饮")
        self.assertEqual(len(results), 0)


if __name__ == '__main__':
    unittest.main()
