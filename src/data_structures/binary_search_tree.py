"""
二叉搜索树 (BST) 实现
时间复杂度分析：
- 插入: 平均 O(log n), 最坏 O(n)
- 删除: 平均 O(log n), 最坏 O(n)
- 查找: 平均 O(log n), 最坏 O(n)
- 遍历: O(n)
特点：左子树 < 根 < 右子树
支持递归遍历（中序、前序、后序）
"""

from typing import Optional, Iterator, TypeVar, Generic, Callable, List
from ..exceptions.custom_exceptions import DataStructureError

T = TypeVar('T')


class BSTNode(Generic[T]):
    """二叉搜索树节点类"""
    
    def __init__(self, data: T):
        self.data: T = data
        self.left: Optional['BSTNode[T]'] = None
        self.right: Optional['BSTNode[T]'] = None
        self._height: int = 1
    
    def update_height(self) -> None:
        """更新节点高度"""
        left_height = self.left._height if self.left else 0
        right_height = self.right._height if self.right else 0
        self._height = 1 + max(left_height, right_height)
    
    def get_height(self) -> int:
        """获取节点高度"""
        return self._height
    
    def get_balance_factor(self) -> int:
        """获取平衡因子"""
        left_height = self.left._height if self.left else 0
        right_height = self.right._height if self.right else 0
        return left_height - right_height
    
    def __repr__(self) -> str:
        return f"BSTNode({self.data})"


class BinarySearchTree(Generic[T]):
    """
    二叉搜索树类
    支持插入、删除、查找操作
    包含递归遍历实现
    """
    
    def __init__(self, key_func: Optional[Callable[[T], any]] = None):
        """
        初始化BST
        :param key_func: 用于比较的关键字提取函数，默认为恒等函数
        """
        self._root: Optional[BSTNode[T]] = None
        self._size: int = 0
        self._key_func = key_func or (lambda x: x)
    
    # ==================== 基本属性 ====================
    
    def is_empty(self) -> bool:
        """检查树是否为空"""
        return self._root is None
    
    def size(self) -> int:
        """返回节点数量"""
        return self._size
    
    def __len__(self) -> int:
        return self._size
    
    def height(self) -> int:
        """获取树高度"""
        return self._root._height if self._root else 0
    
    # ==================== 比较辅助方法 ====================
    
    def _compare(self, data1: T, data2: T) -> int:
        """
        比较两个数据
        返回: <0 表示 data1 < data2, =0 表示相等, >0 表示 data1 > data2
        """
        key1 = self._key_func(data1)
        key2 = self._key_func(data2)
        
        if key1 < key2:
            return -1
        elif key1 > key2:
            return 1
        return 0
    
    # ==================== 插入操作 ====================
    
    def insert(self, data: T) -> None:
        """插入数据 - 平均 O(log n)"""
        self._root = self._insert_recursive(self._root, data)
        self._size += 1
    
    def _insert_recursive(self, node: Optional[BSTNode[T]], data: T) -> BSTNode[T]:
        """递归插入辅助函数"""
        if node is None:
            return BSTNode(data)
        
        comparison = self._compare(data, node.data)
        
        if comparison < 0:
            node.left = self._insert_recursive(node.left, data)
        elif comparison > 0:
            node.right = self._insert_recursive(node.right, data)
        else:
            # 重复数据，更新值
            node.data = data
            self._size -= 1  # 抵消外部的 size 增加
        
        node.update_height()
        return node
    
    # ==================== 查找操作 ====================
    
    def find(self, key: any) -> Optional[T]:
        """根据关键字查找 - 平均 O(log n)"""
        node = self._find_recursive(self._root, key)
        return node.data if node else None
    
    def _find_recursive(self, node: Optional[BSTNode[T]], key: any) -> Optional[BSTNode[T]]:
        """递归查找辅助函数"""
        if node is None:
            return None
        
        node_key = self._key_func(node.data)
        
        if key < node_key:
            return self._find_recursive(node.left, key)
        elif key > node_key:
            return self._find_recursive(node.right, key)
        return node
    
    def contains(self, data: T) -> bool:
        """检查是否包含指定数据"""
        key = self._key_func(data)
        return self.find(key) is not None
    
    def find_min(self) -> Optional[T]:
        """查找最小值"""
        if self._root is None:
            return None
        return self._find_min_node(self._root).data
    
    def _find_min_node(self, node: BSTNode[T]) -> BSTNode[T]:
        """查找最小值节点"""
        while node.left:
            node = node.left
        return node
    
    def find_max(self) -> Optional[T]:
        """查找最大值"""
        if self._root is None:
            return None
        node = self._root
        while node.right:
            node = node.right
        return node.data
    
    # ==================== 删除操作 ====================
    
    def delete(self, key: any) -> bool:
        """删除指定关键字的数据 - 平均 O(log n)"""
        if self.find(key) is None:
            return False
        
        self._root = self._delete_recursive(self._root, key)
        self._size -= 1
        return True
    
    def _delete_recursive(self, node: Optional[BSTNode[T]], key: any) -> Optional[BSTNode[T]]:
        """递归删除辅助函数"""
        if node is None:
            return None
        
        node_key = self._key_func(node.data)
        
        if key < node_key:
            node.left = self._delete_recursive(node.left, key)
        elif key > node_key:
            node.right = self._delete_recursive(node.right, key)
        else:
            # 找到要删除的节点
            if node.left is None:
                return node.right
            elif node.right is None:
                return node.left
            
            # 有两个子节点：找到右子树的最小值替换
            min_node = self._find_min_node(node.right)
            node.data = min_node.data
            node.right = self._delete_recursive(
                node.right, self._key_func(min_node.data)
            )
        
        if node:
            node.update_height()
        return node
    
    # ==================== 递归遍历 ====================
    
    def inorder_traversal(self) -> Iterator[T]:
        """
        中序遍历（左-根-右）- O(n)
        结果按升序排列
        使用递归实现
        """
        yield from self._inorder_recursive(self._root)
    
    def _inorder_recursive(self, node: Optional[BSTNode[T]]) -> Iterator[T]:
        """中序遍历递归辅助函数"""
        if node:
            yield from self._inorder_recursive(node.left)
            yield node.data
            yield from self._inorder_recursive(node.right)
    
    def preorder_traversal(self) -> Iterator[T]:
        """
        前序遍历（根-左-右）- O(n)
        使用递归实现
        """
        yield from self._preorder_recursive(self._root)
    
    def _preorder_recursive(self, node: Optional[BSTNode[T]]) -> Iterator[T]:
        """前序遍历递归辅助函数"""
        if node:
            yield node.data
            yield from self._preorder_recursive(node.left)
            yield from self._preorder_recursive(node.right)
    
    def postorder_traversal(self) -> Iterator[T]:
        """
        后序遍历（左-右-根）- O(n)
        使用递归实现
        """
        yield from self._postorder_recursive(self._root)
    
    def _postorder_recursive(self, node: Optional[BSTNode[T]]) -> Iterator[T]:
        """后序遍历递归辅助函数"""
        if node:
            yield from self._postorder_recursive(node.left)
            yield from self._postorder_recursive(node.right)
            yield node.data
    
    # ==================== 范围查询 ====================
    
    def range_query(self, min_key: any, max_key: any) -> List[T]:
        """范围查询 - O(n)"""
        result = []
        self._range_query_recursive(self._root, min_key, max_key, result)
        return result
    
    def _range_query_recursive(self, node: Optional[BSTNode[T]], 
                                min_key: any, max_key: any, 
                                result: List[T]) -> None:
        """范围查询递归辅助函数"""
        if node is None:
            return
        
        node_key = self._key_func(node.data)
        
        if min_key < node_key:
            self._range_query_recursive(node.left, min_key, max_key, result)
        
        if min_key <= node_key <= max_key:
            result.append(node.data)
        
        if node_key < max_key:
            self._range_query_recursive(node.right, min_key, max_key, result)
    
    # ==================== 转换为列表 ====================
    
    def to_list(self) -> List[T]:
        """转换为有序列表（中序遍历）"""
        return list(self.inorder_traversal())
    
    # ==================== 字符串表示 ====================
    
    def __repr__(self) -> str:
        return f"BinarySearchTree(size={self._size}, height={self.height()})"
    
    def __str__(self) -> str:
        """可视化树结构"""
        if self._root is None:
            return "BinarySearchTree: [空]"
        
        lines = ["BinarySearchTree:"]
        self._str_recursive(self._root, "", True, lines)
        return "\n".join(lines)
    
    def _str_recursive(self, node: Optional[BSTNode[T]], 
                       prefix: str, 
                       is_last: bool, 
                       lines: List[str]) -> None:
        """递归构建字符串表示"""
        if node is None:
            return
        
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{node.data}")
        
        new_prefix = prefix + ("    " if is_last else "│   ")
        
        children = []
        if node.left:
            children.append(('L', node.left))
        if node.right:
            children.append(('R', node.right))
        
        for i, (label, child) in enumerate(children):
            is_last_child = (i == len(children) - 1)
            lines.append(f"{new_prefix}{'    ' if is_last_child else '│   '}[{label}]")
            self._str_recursive(child, new_prefix + ("    " if is_last_child else "│   "), True, lines)
