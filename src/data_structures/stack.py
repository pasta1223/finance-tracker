"""
栈的实现（基于双向链表）
时间复杂度分析：
- 入栈 (push): O(1)
- 出栈 (pop): O(1)
- 查看栈顶 (peek): O(1)
- 判空 (is_empty): O(1)
遵循后进先出 (LIFO) 原则
"""

from typing import TypeVar, Generic, Iterator
from ..exceptions.custom_exceptions import DataStructureError

T = TypeVar('T')


class Stack(Generic[T]):
    """
    栈类 - 后进先出 (LIFO) 数据结构
    使用双向链表作为底层存储
    """
    
    def __init__(self):
        self._items: list[T] = []
    
    # ==================== 基本操作 ====================
    
    def push(self, item: T) -> None:
        """入栈操作 - O(1)"""
        self._items.append(item)
    
    def pop(self) -> T:
        """出栈操作 - O(1)"""
        if self.is_empty():
            raise DataStructureError("Stack", "栈为空，无法执行出栈操作")
        return self._items.pop()
    
    def peek(self) -> T:
        """查看栈顶元素但不移除 - O(1)"""
        if self.is_empty():
            raise DataStructureError("Stack", "栈为空")
        return self._items[-1]
    
    def is_empty(self) -> bool:
        """检查栈是否为空 - O(1)"""
        return len(self._items) == 0
    
    def size(self) -> int:
        """返回栈的大小 - O(1)"""
        return len(self._items)
    
    def clear(self) -> None:
        """清空栈 - O(1)"""
        self._items.clear()
    
    def __len__(self) -> int:
        """返回栈的大小"""
        return self.size()
    
    # ==================== 迭代支持 ====================
    
    def __iter__(self) -> Iterator[T]:
        """从栈顶到栈底的迭代器"""
        return reversed(self._items)
    
    def to_list(self) -> list[T]:
        """转换为列表（栈顶在前）"""
        return list(reversed(self._items))
    
    # ==================== 字符串表示 ====================
    
    def __repr__(self) -> str:
        """字符串表示"""
        items = ", ".join(str(item) for item in self)
        return f"Stack([{items}])"
    
    def __str__(self) -> str:
        """可视化栈结构"""
        if self.is_empty():
            return "Stack: [空]"
        
        lines = ["Stack (栈顶在右):"]
        for i, item in enumerate(self._items):
            marker = " <-- 栈顶" if i == len(self._items) - 1 else ""
            lines.append(f"  [{item}]{marker}")
        return "\n".join(lines)
