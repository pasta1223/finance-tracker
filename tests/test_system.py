"""
系统集成测试
测试完整的用户工作流程
"""

import unittest
import sys
import os
import tempfile
import shutil
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from decimal import Decimal

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.services.transaction_manager import TransactionManager
from src.storage.storage_manager import StorageManager
from src.models.transaction import Transaction, TransactionType
from src.exceptions.custom_exceptions import (
    FinanceTrackerError, ValidationError, NotFoundError
)


class TestEndToEndWorkflow(unittest.TestCase):
    """端到端工作流测试"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.test_dir, "finance_tracker.db")
    
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_complete_workflow(self):
        """完整工作流测试"""
        # 初始化系统
        storage = StorageManager(self.data_file)
        manager = TransactionManager()
        
        # 首次运行 - 添加收入
        print("=== 首次运行 ===")
        t1 = Transaction(
            amount=Decimal("10000"),
            transaction_type=TransactionType.INCOME,
            category="工资",
            description="月薪"
        )
        manager.add(t1)
        print(f"添加收入: {t1.amount}")
        
        # 添加支出
        t2 = Transaction(
            amount=Decimal("3000"),
            transaction_type=TransactionType.EXPENSE,
            category="房租",
            description="月租"
        )
        manager.add(t2)
        print(f"添加支出: {t2.amount}")
        
        # 保存数据
        storage.save_data(manager.to_dict())
        print(f"已保存 {manager.transaction_count} 条记录")
        
        # 模拟程序退出再启动
        print("\n=== 程序重启 ===")
        storage2 = StorageManager(self.data_file)
        manager2 = TransactionManager()
        
        data = storage2.load_data()
        manager2.from_dict(data)
        print(f"加载了 {manager2.transaction_count} 条记录")
        
        # 添加新记录
        t3 = Transaction(
            amount=Decimal("500"),
            transaction_type=TransactionType.EXPENSE,
            category="餐饮",
            description="餐饮消费"
        )
        manager2.add(t3)
        print(f"添加支出: {t2.amount}")
        
        # 查询统计
        balance = manager2.get_balance()
        print(f"\n当前余额: {balance}")
        
        # 按分类统计
        stats = manager2.get_statistics_by_category()
        print(f"分类统计: {stats}")
        
        # 保存更新
        storage2.save_data(manager2.to_dict())
        
        # 再次加载验证
        storage3 = StorageManager(self.data_file)
        manager3 = TransactionManager()
        manager3.from_dict(storage3.load_data())
        
        self.assertEqual(manager3.transaction_count, 3)
        self.assertEqual(manager3.get_balance(), Decimal("6500"))
    
    def test_error_handling(self):
        """错误处理测试"""
        storage = StorageManager(self.data_file)
        manager = TransactionManager()
        
        # 测试无效金额
        with self.assertRaises(ValidationError):
            Transaction(
                amount=Decimal("-100"),
                transaction_type=TransactionType.EXPENSE,
                category="测试"
            )
        
        # 测试空分类
        with self.assertRaises(ValidationError):
            Transaction(
                amount=Decimal("100"),
                transaction_type=TransactionType.EXPENSE,
                category=""
            )
        
        # 测试删除不存在的记录
        with self.assertRaises(NotFoundError):
            manager.remove("nonexistent_id")
    
    def test_undo_redo_workflow(self):
        """撤销重做工作流测试"""
        manager = TransactionManager()
        
        # 添加记录
        t1 = Transaction(
            amount=Decimal("1000"),
            transaction_type=TransactionType.INCOME,
            category="奖金"
        )
        manager.add(t1)
        self.assertEqual(manager.transaction_count, 1)
        
        # 撤销
        manager.undo()
        self.assertEqual(manager.transaction_count, 0)
        
        # 重做
        manager.redo()
        self.assertEqual(manager.transaction_count, 1)
        
        # 验证记录存在
        found = manager.find_by_id(t1.transaction_id)
        self.assertIsNotNone(found)
    
    def test_search_and_filter(self):
        """搜索过滤测试"""
        manager = TransactionManager()
        
        # 添加各种类型的记录
        incomes = [
            Transaction(Decimal("5000"), TransactionType.INCOME, "工资"),
            Transaction(Decimal("1000"), TransactionType.INCOME, "奖金"),
        ]
        expenses = [
            Transaction(Decimal("2000"), TransactionType.EXPENSE, "房租"),
            Transaction(Decimal("500"), TransactionType.EXPENSE, "餐饮"),
            Transaction(Decimal("300"), TransactionType.EXPENSE, "交通"),
        ]
        
        for t in incomes + expenses:
            manager.add(t)
        
        # 按类型搜索
        income_list = manager.find_by_type(TransactionType.INCOME)
        self.assertEqual(len(income_list), 2)
        
        expense_list = manager.find_by_type(TransactionType.EXPENSE)
        self.assertEqual(len(expense_list), 3)
        
        # 按金额范围搜索
        range_results = manager.find_by_amount_range(
            Decimal("500"), 
            Decimal("3000")
        )
        self.assertGreater(len(range_results), 0)
        
        # 按分类搜索
        food_results = manager.find_by_category("餐饮")
        self.assertEqual(len(food_results), 1)


class TestDataIntegrity(unittest.TestCase):
    """数据完整性测试"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.test_dir, "finance_tracker.db")
    
    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_transaction_id_uniqueness(self):
        """测试交易ID唯一性"""
        manager = TransactionManager()
        
        transactions = []
        for i in range(100):
            t = Transaction(
                amount=Decimal("100"),
                transaction_type=TransactionType.INCOME,
                category="测试"
            )
            transactions.append(t)
            manager.add(t)
        
        # 验证所有ID唯一
        ids = [t.transaction_id for t in transactions]
        self.assertEqual(len(ids), len(set(ids)))
    
    def test_persistence_integrity(self):
        """测试持久化完整性"""
        manager = TransactionManager()
        
        # 添加记录并设置不同属性
        t = Transaction(
            amount=Decimal("1234.56"),
            transaction_type=TransactionType.EXPENSE,
            category="餐饮",
            description="测试描述",
            account="测试账户"
        )
        manager.add(t)
        
        # 保存
        storage = StorageManager(self.data_file)
        storage.save_data(manager.to_dict())
        
        # 加载
        manager2 = TransactionManager()
        manager2.from_dict(storage.load_data())
        
        # 验证所有属性完整
        t2 = manager2.find_by_id(t.transaction_id)
        self.assertEqual(t2.amount, Decimal("1234.56"))
        self.assertEqual(t2.category, "餐饮")
        self.assertEqual(t2.description, "测试描述")
        self.assertEqual(t2.account, "测试账户")
        self.assertEqual(t2.transaction_type, TransactionType.EXPENSE)
    
    def test_balance_calculation(self):
        """测试余额计算"""
        manager = TransactionManager()
        
        # 添加收入
        manager.add(Transaction(
            Decimal("10000"),
            TransactionType.INCOME,
            "工资"
        ))
        
        # 添加支出
        manager.add(Transaction(
            Decimal("3000"),
            TransactionType.EXPENSE,
            "房租"
        ))
        manager.add(Transaction(
            Decimal("2000"),
            TransactionType.EXPENSE,
            "购物"
        ))
        
        self.assertEqual(manager.get_total_income(), Decimal("10000"))
        self.assertEqual(manager.get_total_expense(), Decimal("5000"))
        self.assertEqual(manager.get_balance(), Decimal("5000"))


if __name__ == '__main__':
    unittest.main()
