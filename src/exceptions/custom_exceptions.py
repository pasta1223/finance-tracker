"""
自定义异常模块
定义系统中使用的所有自定义异常类
"""


class FinanceTrackerError(Exception):
    """所有财务跟踪系统异常的基类"""
    
    def __init__(self, message: str = "财务跟踪系统错误"):
        self.message = message
        super().__init__(self.message)


class ValidationError(FinanceTrackerError):
    """数据验证错误"""
    
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"[{field}] {message}")


class TransactionError(FinanceTrackerError):
    """交易记录相关错误"""
    
    def __init__(self, transaction_id: str = None, message: str = "交易错误"):
        self.transaction_id = transaction_id
        self.message = message
        super().__init__(f"交易错误 (ID: {transaction_id}): {message}" if transaction_id else message)


class StorageError(FinanceTrackerError):
    """数据存储相关错误"""
    
    def __init__(self, operation: str, message: str):
        self.operation = operation
        self.message = message
        super().__init__(f"存储操作 '{operation}' 失败: {message}")


class DataStructureError(FinanceTrackerError):
    """数据结构操作错误"""
    
    def __init__(self, structure_name: str, message: str):
        self.structure_name = structure_name
        self.message = message
        super().__init__(f"{structure_name} 错误: {message}")


class NotFoundError(FinanceTrackerError):
    """资源未找到错误"""
    
    def __init__(self, resource_type: str, identifier: str):
        self.resource_type = resource_type
        self.identifier = identifier
        super().__init__(f"未找到 {resource_type}: {identifier}")


class DuplicateError(FinanceTrackerError):
    """重复数据错误"""
    
    def __init__(self, resource_type: str, identifier: str):
        self.resource_type = resource_type
        self.identifier = identifier
        super().__init__(f"{resource_type} 已存在: {identifier}")
