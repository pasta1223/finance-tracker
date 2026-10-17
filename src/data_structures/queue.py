"""
队列的实现（基于双向链表）
时间复杂度分析：
- 入队 (enqueue): O(1)
- 出队 (dequeue): O(1)
- 查看队首 (front): O(1)
- 查看队尾 (rear): O(1)
遵循先进先出 (FIFO) 原则
"""

from typing import TypeVar, Generic, Iterator
from ..exceptions.custom_exceptions import DataStructureError

T = TypeVar('T')


class Queue(Generic[T]):
    """
    队列类 - 先进先出 (FIFO) 数据结构
    使用双向链表作为底层存储
    """
    
    def __init__(self):
        self._items: list[T] = []
        self._front_index: int = 0
    
    # ==================== 基本操作 ====================
    
    def enqueue(self, item: T) -> None:
        """入队操作 - O(1)"""
        self._items.append(item)
    
    def dequeue(self) -> T:
        """出队操作 - O(1)"""
        if self.is_empty():
            raise DataStructureError("Queue", "队列为空，无法执行出队操作")
        
        item = self._items[self._front_index]
        self._front_index += 1
        
        # 定期清理已出队元素，防止内存无限增长
        if self._front_index > len(self._items) // 2:
            self._items = self._items[self._front_index:]
            self._front_index = 0
        
        return item
    
    def front(self) -> T:
        """查看队首元素 - O(1)"""
        if self.is_empty():
            raise DataStructureError("Queue", "队列为空")
        return self._items[self._front_index]
    
    def rear(self) -> T:
        """查看队尾元素 - O(1)"""
        if self.is_empty():
            raise DataStructureError("Queue", "队列为空")
        return self._items[-1]
    
    def is_empty(self) -> bool:
        """检查队列是否为空 - O(1)"""
        return self._front_index >= len(self._items)
    
    def size(self) -> int:
        """返回队列大小 - O(1)"""
        return len(self._items) - self._front_index
    
    def __len__(self) -> int:
        """返回队列大小"""
        return self.size()
    
    # ==================== 迭代支持 ====================
    
    def __iter__(self) -> Iterator[T]:
        """从队首到队尾的迭代器"""
        for i in range(self._front_index, len(self._items)):
            yield self._items[i]
    
    def to_list(self) -> list[T]:
        """转换为列表（队首在前）"""
        return list(self)
    
    # ==================== 字符串表示 ====================
    
    def __repr__(self) -> str:
        """字符串表示"""
        items = ", ".join(str(item) for item in self)
        return f"Queue([{items}])"
    
    def __str__(self) -> str:
        """可视化队列结构"""
        if self.is_empty():
            return "Queue: [空]"
        
        lines = ["Queue (队首 <- 队尾):"]
        items = list(self)
        for i, item in enumerate(items):
            markers = []
            if i == 0:
                markers.append("队首")
            if i == len(items) - 1:
                markers.append("队尾")
            marker = f" <-- {', '.join(markers)}" if markers else ""
            lines.append(f"  [{item}]{marker}")
        return "\n".join(lines)
