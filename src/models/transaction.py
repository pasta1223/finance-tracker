"""
交易记录模型
定义交易记录的数据结构和行为
"""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum, auto
from typing import Optional
import uuid

from ..exceptions.custom_exceptions import ValidationError


class TransactionType(Enum):
    """交易类型枚举"""
    INCOME = "Income"
    EXPENSE = "Expense"
    TRANSFER = "Transfer"
    
    def __str__(self) -> str:
        return self.value


class Transaction:
    """
    交易记录类
    封装交易的所有属性和验证逻辑
    """
    
    def __init__(
        self,
        amount: Decimal,
        transaction_type: TransactionType,
        category: str,
        description: str = "",
        account: str = "Default account",
        transaction_date: Optional[datetime] = None,
        transaction_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        author_id: str = "",
        author_name: str = ""
    ):
        """
        初始化交易记录
        
        :param amount: 金额（必须为正数）
        :param transaction_type: 交易类型
        :param category: 分类
        :param description: 描述
        :param account: 账户
        :param transaction_date: 交易日期，默认为当前时间
        :param transaction_id: 交易ID，默认自动生成
        :param created_at: 创建时间
        """
        self._transaction_id = transaction_id or str(uuid.uuid4())[:8]
        self._created_at = created_at or datetime.now()
        self._author_id = author_id
        self._author_name = author_name
        
        # 验证并设置金额
        self.amount = amount
        
        # 验证并设置交易类型
        self.transaction_type = transaction_type
        
        # 验证并设置分类
        self.category = category
        
        # 可选字段
        self.description = description
        self.account = account
        self.transaction_date = transaction_date or datetime.now()
    
    # ==================== 属性访问器 ====================
    
    @property
    def author_id(self) -> str:
        return self._author_id

    @property
    def author_name(self) -> str:
        return self._author_name

    @property
    def transaction_id(self) -> str:
        """交易ID（只读）"""
        return self._transaction_id
    
    @property
    def created_at(self) -> datetime:
        """创建时间（只读）"""
        return self._created_at
    
    @property
    def amount(self) -> Decimal:
        """金额"""
        return self._amount
    
    @amount.setter
    def amount(self, value: Decimal) -> None:
        """设置金额（带验证）"""
        if not isinstance(value, Decimal):
            try:
                value = Decimal(str(value))
            except:
                raise ValidationError("amount", "Amount must be a Decimal")
        
        if not value.is_finite() or value <= 0:
            raise ValidationError("amount", "Amount must be greater than 0")
        
        # 保留两位小数
        self._amount = value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @property
    def transaction_type(self) -> TransactionType:
        """交易类型"""
        return self._transaction_type
    
    @transaction_type.setter
    def transaction_type(self, value: TransactionType) -> None:
        """设置交易类型（带验证）"""
        if not isinstance(value, TransactionType):
            raise ValidationError("transaction_type", "Invalid transaction type")
        self._transaction_type = value
    
    @property
    def category(self) -> str:
        """分类"""
        return self._category
    
    @category.setter
    def category(self, value: str) -> None:
        """设置分类（带验证）"""
        if not value or not value.strip():
            raise ValidationError("category", "Category must not be empty")
        self._category = value.strip()
    
    @property
    def description(self) -> str:
        """描述"""
        return self._description
    
    @description.setter
    def description(self, value: str) -> None:
        """设置描述"""
        self._description = value.strip() if value else ""
    
    @property
    def account(self) -> str:
        """账户"""
        return self._account
    
    @account.setter
    def account(self, value: str) -> None:
        """设置账户（带验证）"""
        if not value or not value.strip():
            raise ValidationError("account", "Account must not be empty")
        self._account = value.strip()
    
    @property
    def transaction_date(self) -> datetime:
        """交易日期"""
        return self._transaction_date
    
    @transaction_date.setter
    def transaction_date(self, value: datetime) -> None:
        """设置交易日期（带验证）"""
        if not isinstance(value, datetime):
            raise ValidationError("transaction_date", "Invalid transaction date")
        self._transaction_date = value
    
    # ==================== 业务方法 ====================
    
    def get_signed_amount(self) -> Decimal:
        """
        获取带符号的金额
        收入为正，支出为负
        """
        if self._transaction_type == TransactionType.EXPENSE:
            return -self._amount
        return self._amount
    
    def update(self, **kwargs) -> None:
        """
        批量更新属性
        """
        for key, value in kwargs.items():
            if hasattr(self, key) and not key.startswith('_'):
                setattr(self, value)
            else:
                raise ValidationError(key, f"Non-existent attributes cannot be updated: {key}")
    
    # ==================== 序列化 ====================
    
    def to_dict(self) -> dict:
        """转换为字典（用于序列化）"""
        return {
            "transaction_id": self._transaction_id,
            "amount": str(self._amount),
            "transaction_type": self._transaction_type.name,
            "category": self._category,
            "description": self._description,
            "account": self._account,
            "transaction_date": self._transaction_date.isoformat(),
            "created_at": self._created_at.isoformat(),
            "author_id": self._author_id,
            "author_name": self._author_name
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Transaction':
        """从字典创建实例（用于反序列化）"""
        return cls(
            transaction_id=data.get("transaction_id"),
            amount=Decimal(data["amount"]),
            transaction_type=TransactionType[data["transaction_type"]],
            category=data["category"],
            description=data.get("description", ""),
            account=data.get("account", "Default account"),
            transaction_date=datetime.fromisoformat(data["transaction_date"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            author_id=data.get("author_id", ""),
            author_name=data.get("author_name", "")
        )
    
    # ==================== 字符串表示 ====================
    
    def __repr__(self) -> str:
        return (
            f"Transaction(id={self._transaction_id}, "
            f"amount={self._amount}, "
            f"type={self._transaction_type.value}, "
            f"category={self._category})"
        )
    
    def __str__(self) -> str:
        sign = "+" if self._transaction_type == TransactionType.INCOME else "-"
        return (
            f"[{self._transaction_date.strftime('%Y-%m-%d')}] "
            f"{sign}¥{self._amount} | "
            f"{self._transaction_type.value} | "
            f"{self._category} | "
            f"{self._description or 'No description'}"
        )
    
    def __eq__(self, other: object) -> bool:
        """相等比较（基于交易ID）"""
        if not isinstance(other, Transaction):
            return False
        return self._transaction_id == other._transaction_id
    
    def __hash__(self) -> int:
        """哈希值（基于交易ID）"""
        return hash(self._transaction_id)
