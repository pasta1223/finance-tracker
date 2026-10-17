"""
哈希表实现（链地址法解决冲突）
时间复杂度分析：
- 插入: 平均 O(1), 最坏 O(n)
- 删除: 平均 O(1), 最坏 O(n)
- 查找: 平均 O(1), 最坏 O(n)
- 扩容: O(n)
使用动态扩容保持负载因子在合理范围
"""

from typing import Optional, TypeVar, Generic, Iterator, List, Tuple
from ..exceptions.custom_exceptions import DataStructureError

T = TypeVar('T')


class HashNode(Generic[T]):
    """哈希表节点类（用于链地址法）"""
    
    def __init__(self, key: str, value: T):
        self.key: str = key
        self.value: T = value
        self.next: Optional['HashNode[T]'] = None
    
    def __repr__(self) -> str:
        return f"HashNode({self.key}: {self.value})"


class HashTable(Generic[T]):
    """
    哈希表类
    使用链地址法解决冲突
    支持动态扩容
    """
    
    # 默认初始容量和负载因子阈值
    DEFAULT_CAPACITY = 16
    LOAD_FACTOR_THRESHOLD = 0.75
    
    def __init__(self, capacity: int = DEFAULT_CAPACITY):
        self._capacity: int = capacity
        self._size: int = 0
        self._buckets: List[Optional[HashNode[T]]] = [None] * capacity
        self._modification_count: int = 0
    
    # ==================== 基本属性 ====================
    
    def __len__(self) -> int:
        """返回元素数量"""
        return self._size
    
    def is_empty(self) -> bool:
        """检查是否为空"""
        return self._size == 0
    
    def _load_factor(self) -> float:
        """计算当前负载因子"""
        return self._size / self._capacity
    
    # ==================== 哈希函数 ====================
    
    def _hash(self, key: str) -> int:
        """
        哈希函数 - 使用简单的多项式滚动哈希
        时间复杂度: O(k)，k为键的长度
        """
        hash_value = 0
        for char in key:
            hash_value = (hash_value * 31 + ord(char)) & 0xFFFFFFFF
        return hash_value % self._capacity
    
    # ==================== 基本操作 ====================
    
    def put(self, key: str, value: T) -> None:
        """
        插入或更新键值对 - 平均 O(1)
        """
        if not key:
            raise DataStructureError("HashTable", "键不能为空")
        
        # 检查是否需要扩容
        if self._load_factor() > self.LOAD_FACTOR_THRESHOLD:
            self._resize()
        
        index = self._hash(key)
        new_node = HashNode(key, value)
        
        if self._buckets[index] is None:
            # 桶为空，直接插入
            self._buckets[index] = new_node
            self._size += 1
            self._modification_count += 1
        else:
            # 处理冲突 - 链地址法
            current = self._buckets[index]
            
            # 检查是否已存在相同键
            while current:
                if current.key == key:
                    # 更新现有值
                    current.value = value
                    return
                if current.next is None:
                    break
                current = current.next
            
            # 在链表尾部添加新节点
            current.next = new_node
            self._size += 1
            self._modification_count += 1
    
    def get(self, key: str) -> Optional[T]:
        """
        根据键获取值 - 平均 O(1)
        """
        if not key:
            return None
        
        index = self._hash(key)
        current = self._buckets[index]
        
        while current:
            if current.key == key:
                return current.value
            current = current.next
        
        return None
    
    def remove(self, key: str) -> bool:
        """
        删除键值对 - 平均 O(1)
        """
        if not key:
            return False
        
        index = self._hash(key)
        current = self._buckets[index]
        
        if current is None:
            return False
        
        # 检查头节点
        if current.key == key:
            self._buckets[index] = current.next
            self._size -= 1
            self._modification_count += 1
            return True
        
        # 遍历链表查找
        while current.next:
            if current.next.key == key:
                current.next = current.next.next
                self._size -= 1
                self._modification_count += 1
                return True
            current = current.next
        
        return False
    
    def contains_key(self, key: str) -> bool:
        """检查是否包含指定键"""
        return self.get(key) is not None
    
    # ==================== 扩容 ====================
    
    def _resize(self) -> None:
        """
        扩容操作 - O(n)
        当负载因子超过阈值时，将容量翻倍并重新哈希所有元素
        """
        old_buckets = self._buckets
        old_capacity = self._capacity
        
        # 容量翻倍
        self._capacity *= 2
        self._buckets = [None] * self._capacity
        self._size = 0
        
        # 重新哈希所有元素
        for i in range(old_capacity):
            current = old_buckets[i]
            while current:
                self.put(current.key, current.value)
                current = current.next
        
        self._modification_count += 1
    
    # ==================== 迭代支持 ====================
    
    def keys(self) -> Iterator[str]:
        """遍历所有键"""
        for bucket in self._buckets:
            current = bucket
            while current:
                yield current.key
                current = current.next
    
    def values(self) -> Iterator[T]:
        """遍历所有值"""
        for bucket in self._buckets:
            current = bucket
            while current:
                yield current.value
                current = current.next
    
    def items(self) -> Iterator[Tuple[str, T]]:
        """遍历所有键值对"""
        for bucket in self._buckets:
            current = bucket
            while current:
                yield (current.key, current.value)
                current = current.next
    
    def __iter__(self) -> Iterator[str]:
        """默认迭代键"""
        return self.keys()
    
    # ==================== 批量操作 ====================
    
    def clear(self) -> None:
        """清空哈希表"""
        self._buckets = [None] * self._capacity
        self._size = 0
        self._modification_count += 1
    
    def to_dict(self) -> dict:
        """转换为Python字典"""
        return {key: self.get(key) for key in self.keys()}
    
    # ==================== 字符串表示 ====================
    
    def __repr__(self) -> str:
        """字符串表示"""
        items = []
        for key, value in self.items():
            items.append(f"{key!r}: {value!r}")
        return f"HashTable({{'{', '.join(items)}}})"
    
    def __str__(self) -> str:
        """可视化哈希表结构"""
        lines = [
            f"HashTable (size={self._size}, capacity={self._capacity}, "
            f"load_factor={self._load_factor():.2f}):"
        ]
        
        for i, bucket in enumerate(self._buckets):
            if bucket:
                chain = []
                current = bucket
                while current:
                    chain.append(f"{current.key}={current.value}")
                    current = current.next
                lines.append(f"  Bucket[{i}]: {' -> '.join(chain)}")
        
        return "\n".join(lines)
    
    def get_stats(self) -> dict:
        """获取哈希表统计信息"""
        non_empty_buckets = sum(1 for b in self._buckets if b is not None)
        chain_lengths = []
        
        for bucket in self._buckets:
            length = 0
            current = bucket
            while current:
                length += 1
                current = current.next
            if length > 0:
                chain_lengths.append(length)
        
        return {
            "size": self._size,
            "capacity": self._capacity,
            "load_factor": self._load_factor(),
            "non_empty_buckets": non_empty_buckets,
            "max_chain_length": max(chain_lengths) if chain_lengths else 0,
            "avg_chain_length": sum(chain_lengths) / len(chain_lengths) if chain_lengths else 0
        }
