"""
导出模块测试
"""

import unittest
import os
import tempfile
import shutil
from datetime import datetime
from decimal import Decimal

from src.export.exporter import ExportManager, CSVExporter, TextReportExporter
from src.models.transaction import Transaction, TransactionType


class TestExporters(unittest.TestCase):
    """测试导出器"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.transactions = [
            Transaction(
                amount=Decimal('1000'),
                transaction_type=TransactionType.INCOME,
                category="工资",
                description="月薪",
                account="主账户"
            ),
            Transaction(
                amount=Decimal('200'),
                transaction_type=TransactionType.EXPENSE,
                category="餐饮",
                description="午餐",
                account="主账户"
            )
        ]
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_csv_export(self):
        """测试CSV导出"""
        exporter = CSVExporter()
        filepath = os.path.join(self.temp_dir, "test.csv")
        
        result = exporter.export(self.transactions, filepath)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filepath))
        
        # 验证内容
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            self.assertIn('交易ID', content)
            self.assertIn('工资', content)
    
    def test_text_report_export(self):
        """测试文本报表导出"""
        exporter = TextReportExporter()
        filepath = os.path.join(self.temp_dir, "test_report.txt")
        
        result = exporter.export(self.transactions, filepath)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filepath))
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('财务报表', content)
            self.assertIn('收支汇总', content)


class TestExportManager(unittest.TestCase):
    """测试ExportManager"""
    
    def test_get_available_formats(self):
        """测试获取可用格式"""
        formats = ExportManager.get_available_formats()
        self.assertIn('csv', formats)
        self.assertIn('report', formats)
        self.assertNotIn('json', formats)
    
    def test_export_with_auto_name(self):
        """测试自动命名导出"""
        temp_dir = tempfile.mkdtemp()
        try:
            transactions = [
                Transaction(
                    amount=Decimal('100'),
                    transaction_type=TransactionType.INCOME,
                    category="工资"
                )
            ]
            filepath = ExportManager.export_with_auto_name(transactions, temp_dir, 'csv')
            self.assertTrue(os.path.exists(filepath))
            self.assertTrue(filepath.endswith('.csv'))
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


if __name__ == '__main__':
    unittest.main()
