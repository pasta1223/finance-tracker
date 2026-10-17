"""
预算管理测试
"""

import unittest
from decimal import Decimal

from src.services.budget_manager import BudgetManager, Budget
from src.exceptions.custom_exceptions import ValidationError


class TestBudget(unittest.TestCase):
    """测试Budget"""
    
    def test_budget_properties(self):
        """测试预算属性"""
        budget = Budget(
            category="餐饮",
            amount=Decimal('1000'),
            spent=Decimal('300'),
            month=4,
            year=2026
        )
        self.assertEqual(budget.remaining, Decimal('700'))
        self.assertAlmostEqual(budget.usage_percentage, 30.0)
        self.assertFalse(budget.is_exceeded)
        
        # 超支情况
        budget.spent = Decimal('1200')
        self.assertTrue(budget.is_exceeded)


class TestBudgetManager(unittest.TestCase):
    """测试BudgetManager"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = BudgetManager()
    
    def test_set_monthly_budget(self):
        """测试设置月度预算"""
        self.manager.set_monthly_budget(2026, 4, Decimal('5000'))
        budget = self.manager.get_monthly_budget(2026, 4)
        self.assertEqual(budget, Decimal('5000'))
    
    def test_set_category_budget(self):
        """测试设置分类预算"""
        budget = self.manager.set_category_budget("餐饮", 2026, 4, Decimal('1000'))
        self.assertIsNotNone(budget)
        self.assertEqual(budget.amount, Decimal('1000'))
        self.assertEqual(budget.category, "餐饮")
    
    def test_add_spending(self):
        """测试增加支出"""
        self.manager.set_category_budget("餐饮", 2026, 4, Decimal('1000'))
        self.manager.add_category_spending("餐饮", 2026, 4, Decimal('300'))
        
        budget = self.manager.get_category_budget("餐饮", 2026, 4)
        self.assertEqual(budget.spent, Decimal('300'))
    
    def test_budget_alerts(self):
        """测试预算警告"""
        self.manager.set_monthly_budget(2026, 4, Decimal('1000'))
        
        # 警告阈值80%
        alerts = self.manager.check_budget_alerts(2026, 4, Decimal('850'))
        self.assertTrue(len(alerts) > 0)
        
        # 超支
        alerts = self.manager.check_budget_alerts(2026, 4, Decimal('1100'))
        self.assertTrue(any("超支" in a for a in alerts))
    
    def test_serialization(self):
        """测试序列化"""
        self.manager.set_monthly_budget(2026, 4, Decimal('5000'))
        self.manager.set_category_budget("餐饮", 2026, 4, Decimal('1000'))
        
        data = self.manager.to_dict()
        self.assertIn('monthly_budgets', data)
        self.assertIn('category_budgets', data)
        
        # 测试反序列化
        new_manager = BudgetManager()
        new_manager.from_dict(data)
        self.assertEqual(new_manager.get_monthly_budget(2026, 4), Decimal('5000'))


if __name__ == '__main__':
    unittest.main()
