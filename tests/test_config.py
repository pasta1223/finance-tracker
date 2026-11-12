"""
配置模块测试
"""

import unittest
import os
import tempfile
import shutil
import sqlite3

from src.core.config import ConfigManager, AppConfig
from src.version import APP_VERSION


class TestAppConfig(unittest.TestCase):
    """测试AppConfig"""
    
    def test_default_values(self):
        """测试默认值"""
        config = AppConfig()
        self.assertEqual(config.app_name, "个人财务跟踪系统")
        self.assertEqual(config.app_version, APP_VERSION)
        self.assertTrue(config.auto_save)
    
    def test_to_dict(self):
        """测试序列化"""
        config = AppConfig(app_name="Test", monthly_budget=5000.0)
        data = config.to_dict()
        self.assertEqual(data['app_name'], "Test")
        self.assertEqual(data['monthly_budget'], 5000.0)
    
    def test_from_dict(self):
        """测试反序列化"""
        data = {
            'app_name': 'Test App',
            'app_version': '2.0.0',
            'auto_save': False,
            'log_enabled': True,
            'log_file': 'test.log',
            'log_level': 'DEBUG',
            'currency_symbol': '$',
            'date_format': '%Y/%m/%d',
            'datetime_format': '%Y/%m/%d %H:%M',
            'decimal_places': 2,
            'monthly_budget': 1000.0,
            'budget_alert_threshold': 0.9,
            'income_categories': ['Salary'],
            'expense_categories': ['Food'],
            'default_account': 'Test Account',
            'accounts': ['Account1']
        }
        config = AppConfig.from_dict(data)
        self.assertEqual(config.app_name, 'Test App')
        self.assertEqual(config.currency_symbol, '$')


class TestConfigManager(unittest.TestCase):
    """测试ConfigManager"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.database_path = os.path.join(self.temp_dir, 'finance_tracker.db')
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_new_config(self):
        """测试新配置"""
        ConfigManager(self.database_path)
        self.assertTrue(os.path.exists(self.database_path))
        connection = sqlite3.connect(self.database_path)
        try:
            table = connection.execute(
                "SELECT name FROM sqlite_master WHERE name = 'app_config'"
            ).fetchone()
        finally:
            connection.close()
        self.assertIsNotNone(table)
    
    def test_get_set(self):
        """测试获取和设置"""
        manager = ConfigManager(self.database_path)
        manager.set('monthly_budget', 5000.0)
        reloaded = ConfigManager(self.database_path)
        self.assertEqual(reloaded.get('monthly_budget'), 5000.0)
    
    def test_reset(self):
        """测试重置"""
        manager = ConfigManager(self.database_path)
        manager.set('monthly_budget', 9999.0)
        manager.reset_to_default()
        self.assertEqual(manager.get('monthly_budget'), 0.0)

    def test_stale_application_version_is_upgraded(self):
        """应用版本随已安装代码升级，不保留旧数据库中的版本号。"""
        manager = ConfigManager(self.database_path)
        manager.set('app_version', '1.0.0')

        reloaded = ConfigManager(self.database_path)

        self.assertEqual(reloaded.get('app_version'), APP_VERSION)


if __name__ == '__main__':
    unittest.main()
