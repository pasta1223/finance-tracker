"""
日志系统模块
提供应用程序的日志记录功能
"""

import os
import logging
from datetime import datetime
from enum import Enum
from typing import Optional
from logging.handlers import RotatingFileHandler


class LogLevel(Enum):
    """日志级别"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class Logger:
    """
    日志记录器
    支持文件和控制台双输出，支持日志轮转
    """
    
    def __init__(
        self,
        name: str = "FinanceTracker",
        log_file: str = "data/app.log",
        level: LogLevel = LogLevel.INFO,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 3
    ):
        self._name = name
        self._log_file = log_file
        self._level = level
        self._logger: Optional[logging.Logger] = None
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._init_logger()
    
    def _init_logger(self) -> None:
        """初始化日志记录器"""
        self._logger = logging.getLogger(self._name)
        self._logger.setLevel(self._level.value)
        
        # 避免重复添加handler
        if self._logger.handlers:
            return
        
        # 格式化器
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 确保日志目录存在
        log_dir = os.path.dirname(self._log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 文件处理器（带日志轮转）
        try:
            file_handler = RotatingFileHandler(
                self._log_file,
                maxBytes=self._max_bytes,
                backupCount=self._backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self._level.value)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
        except IOError as e:
            print(f"[警告] 无法创建日志文件: {e}")
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self._level.value)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)
    
    def debug(self, message: str) -> None:
        """记录调试信息"""
        self._logger.debug(message)
    
    def info(self, message: str) -> None:
        """记录一般信息"""
        self._logger.info(message)
    
    def warning(self, message: str) -> None:
        """记录警告信息"""
        self._logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False) -> None:
        """记录错误信息"""
        self._logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str) -> None:
        """记录严重错误"""
        self._logger.critical(message)
    
    def log_action(self, action: str, details: str = "") -> None:
        """记录用户操作"""
        msg = f"[操作] {action}"
        if details:
            msg += f" - {details}"
        self._logger.info(msg)
    
    def log_transaction(self, action: str, transaction_id: str, amount: float) -> None:
        """记录交易操作"""
        msg = f"[交易] {action} - ID: {transaction_id}, 金额: {amount}"
        self._logger.info(msg)
    
    def set_level(self, level: LogLevel) -> None:
        """设置日志级别"""
        self._level = level
        self._logger.setLevel(level.value)
        for handler in self._logger.handlers:
            handler.setLevel(level.value)


# 全局日志实例
_app_logger: Optional[Logger] = None


def get_logger(
    name: str = "FinanceTracker",
    log_file: str = "data/app.log",
    level: LogLevel = LogLevel.INFO
) -> Logger:
    """获取全局日志实例"""
    global _app_logger
    if _app_logger is None:
        _app_logger = Logger(name, log_file, level)
    return _app_logger


def init_logger(config) -> Logger:
    """根据配置初始化日志"""
    level_map = {
        "DEBUG": LogLevel.DEBUG,
        "INFO": LogLevel.INFO,
        "WARNING": LogLevel.WARNING,
        "ERROR": LogLevel.ERROR
    }
    level = level_map.get(config.get("log_level", "INFO"), LogLevel.INFO)
    return get_logger(
        log_file=config.get("log_file", "data/app.log"),
        level=level
    )
