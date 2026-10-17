"""
分类模型
定义收支分类的数据结构
"""

from typing import Optional, List
from decimal import Decimal

from ..exceptions.custom_exceptions import ValidationError


class Category:
    """
    分类类
    用于组织和管理收支分类
    """
    
    def __init__(
        self,
        name: str,
        category_type: str,  # "income" 或 "expense"
        description: str = "",
        parent: Optional['Category'] = None,
        budget_limit: Optional[Decimal] = None
    ):
        """
        初始化分类
        
        :param name: 分类名称
        :param category_type: 分类类型 (income/expense)
        :param description: 描述
        :param parent: 父分类
        :param budget_limit: 预算上限（仅支出分类）
        """
        self.name = name
        self.category_type = category_type
        self.description = description
        self.parent = parent
        self.budget_limit = budget_limit
        self._subcategories: List['Category'] = []
        
        # 如果有父分类，将自己添加到父分类的子分类列表
        if parent:
            parent.add_subcategory(self)
    
    # ==================== 属性访问器 ====================
    
    @property
    def name(self) -> str:
        """分类名称"""
        return self._name
    
    @name.setter
    def name(self, value: str) -> None:
        """设置分类名称（带验证）"""
        if not value or not value.strip():
            raise ValidationError("name", "分类名称不能为空")
        self._name = value.strip()
    
    @property
    def category_type(self) -> str:
        """分类类型"""
        return self._category_type
    
    @category_type.setter
    def category_type(self, value: str) -> None:
        """设置分类类型（带验证）"""
        value = value.lower().strip()
        if value not in ("income", "expense"):
            raise ValidationError("category_type", "分类类型必须是 'income' 或 'expense'")
        self._category_type = value
    
    @property
    def full_path(self) -> str:
        """获取完整路径（包含父分类）"""
        if self.parent:
            return f"{self.parent.full_path} > {self._name}"
        return self._name
    
    @property
    def subcategories(self) -> List['Category']:
        """获取子分类列表"""
        return self._subcategories.copy()
    
    @property
    def is_root(self) -> bool:
        """是否为根分类"""
        return self.parent is None
    
    @property
    def is_leaf(self) -> bool:
        """是否为叶子分类"""
        return len(self._subcategories) == 0
    
    # ==================== 子分类管理 ====================
    
    def add_subcategory(self, subcategory: 'Category') -> None:
        """添加子分类"""
        if subcategory not in self._subcategories:
            self._subcategories.append(subcategory)
            subcategory.parent = self
    
    def remove_subcategory(self, subcategory: 'Category') -> bool:
        """移除子分类"""
        if subcategory in self._subcategories:
            self._subcategories.remove(subcategory)
            subcategory.parent = None
            return True
        return False
    
    def get_all_subcategories(self) -> List['Category']:
        """获取所有子分类（递归）"""
        result = []
        for sub in self._subcategories:
            result.append(sub)
            result.extend(sub.get_all_subcategories())
        return result
    
    # ==================== 序列化 ====================
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self._name,
            "category_type": self._category_type,
            "description": self.description,
            "parent": self.parent.name if self.parent else None,
            "budget_limit": str(self.budget_limit) if self.budget_limit else None,
            "subcategories": [sub.name for sub in self._subcategories]
        }
    
    # ==================== 字符串表示 ====================
    
    def __repr__(self) -> str:
        return f"Category({self.full_path}, type={self._category_type})"
    
    def __str__(self) -> str:
        return self.full_path
    
    def __eq__(self, other: object) -> bool:
        """相等比较"""
        if not isinstance(other, Category):
            return False
        return self.full_path == other.full_path
    
    def __hash__(self) -> int:
        """哈希值"""
        return hash(self.full_path)
