"""
双向链表实现
时间复杂度分析：
- 头部插入/删除: O(1)
- 尾部插入/删除: O(1)
- 中间插入/删除: O(n)
- 查找: O(n)
"""

from typing import Optional, Iterator, TypeVar, Generic, Callable
from ..exceptions.custom_exceptions import DataStructureError

T = TypeVar('T')


class Node(Generic[T]):
    """双向链表节点类"""
    
    def __init__(self, data: T):
        self.data: T = data
        self.prev: Optional['Node[T]'] = None
        self.next: Optional['Node[T]'] = None
    
    def __repr__(self) -> str:
        return f"Node({self.data})"


class DoublyLinkedList(Generic[T]):
    """
    双向链表类
    支持在头部、尾部和任意位置进行高效插入和删除
    """
    
    def __init__(self):
        self._head: Optional[Node[T]] = None
        self._tail: Optional[Node[T]] = None
        self._size: int = 0
    
    # ==================== 基本属性 ====================
    
    def __len__(self) -> int:
        """返回链表长度"""
        return self._size
    
    def is_empty(self) -> bool:
        """检查链表是否为空"""
        return self._size == 0
    
    def __iter__(self) -> Iterator[T]:
        """正向迭代器"""
        current = self._head
        while current:
            yield current.data
            current = current.next
    
    def __reversed__(self) -> Iterator[T]:
        """反向迭代器"""
        current = self._tail
        while current:
            yield current.data
            current = current.prev
    
    # ==================== 插入操作 ====================
    
    def append(self, data: T) -> None:
        """在尾部添加元素 - O(1)"""
        new_node = Node(data)
        
        if self.is_empty():
            self._head = self._tail = new_node
        else:
            new_node.prev = self._tail
            self._tail.next = new_node
            self._tail = new_node
        
        self._size += 1
    
    def prepend(self, data: T) -> None:
        """在头部添加元素 - O(1)"""
        new_node = Node(data)
        
        if self.is_empty():
            self._head = self._tail = new_node
        else:
            new_node.next = self._head
            self._head.prev = new_node
            self._head = new_node
        
        self._size += 1
    
    def insert_at(self, index: int, data: T) -> None:
        """在指定位置插入元素 - O(n)"""
        if index < 0 or index > self._size:
            raise DataStructureError("DoublyLinkedList", f"索引 {index} 超出范围")
        
        if index == 0:
            self.prepend(data)
        elif index == self._size:
            self.append(data)
        else:
            new_node = Node(data)
            current = self._get_node_at(index)
            
            new_node.prev = current.prev
            new_node.next = current
            current.prev.next = new_node
            current.prev = new_node
            
            self._size += 1
    
    # ==================== 删除操作 ====================
    
    def remove(self, data: T) -> bool:
        """删除第一个匹配的元素 - O(n)"""
        current = self._head
        
        while current:
            if current.data == data:
                self._remove_node(current)
                return True
            current = current.next
        
        return False
    
    def remove_at(self, index: int) -> T:
        """删除指定位置的元素 - O(n)"""
        if index < 0 or index >= self._size:
            raise DataStructureError("DoublyLinkedList", f"索引 {index} 超出范围")
        
        node = self._get_node_at(index)
        self._remove_node(node)
        return node.data
    
    def pop(self) -> T:
        """删除并返回尾部元素 - O(1)"""
        if self.is_empty():
            raise DataStructureError("DoublyLinkedList", "链表为空")
        
        data = self._tail.data
        self._remove_node(self._tail)
        return data
    
    def popleft(self) -> T:
        """删除并返回头部元素 - O(1)"""
        if self.is_empty():
            raise DataStructureError("DoublyLinkedList", "链表为空")
        
        data = self._head.data
        self._remove_node(self._head)
        return data
    
    def _remove_node(self, node: Node[T]) -> None:
        """删除指定节点 - O(1)"""
        if node.prev:
            node.prev.next = node.next
        else:
            self._head = node.next
        
        if node.next:
            node.next.prev = node.prev
        else:
            self._tail = node.prev
        
        self._size -= 1
    
    # ==================== 查找操作 ====================
    
    def find(self, predicate: Callable[[T], bool]) -> Optional[T]:
        """根据条件查找第一个匹配的元素 - O(n)"""
        for item in self:
            if predicate(item):
                return item
        return None
    
    def find_all(self, predicate: Callable[[T], bool]) -> list[T]:
        """根据条件查找所有匹配的元素 - O(n)"""
        return [item for item in self if predicate(item)]
    
    def index_of(self, data: T) -> int:
        """查找元素的索引 - O(n)"""
        current = self._head
        index = 0
        
        while current:
            if current.data == data:
                return index
            current = current.next
            index += 1
        
        return -1
    
    def contains(self, data: T) -> bool:
        """检查是否包含指定元素 - O(n)"""
        return self.index_of(data) != -1
    
    def get(self, index: int) -> T:
        """获取指定位置的元素 - O(n)"""
        if index < 0 or index >= self._size:
            raise DataStructureError("DoublyLinkedList", f"索引 {index} 超出范围")
        
        return self._get_node_at(index).data
    
    def _get_node_at(self, index: int) -> Node[T]:
        """获取指定位置的节点 - O(n)，但会优化选择遍历方向"""
        # 优化：根据索引位置选择从头部还是尾部开始遍历
        if index < self._size // 2:
            current = self._head
            for _ in range(index):
                current = current.next
        else:
            current = self._tail
            for _ in range(self._size - 1 - index):
                current = current.prev
        
        return current
    
    # ==================== 其他操作 ====================
    
    def clear(self) -> None:
        """清空链表 - O(1)"""
        self._head = None
        self._tail = None
        self._size = 0
    
    def to_list(self) -> list[T]:
        """转换为Python列表 - O(n)"""
        return list(self)
    
    def __repr__(self) -> str:
        """字符串表示"""
        items = ", ".join(str(item) for item in self)
        return f"DoublyLinkedList([{items}])"
