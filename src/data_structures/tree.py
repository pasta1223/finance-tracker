"""
通用树结构实现
时间复杂度分析：
- 插入子节点: O(1)
- 删除节点: O(n) 需要查找
- 查找节点: O(n)
- 遍历: O(n)
支持递归遍历（前序、后序、层序）
"""

from typing import Optional, Iterator, TypeVar, Generic, List, Callable
from collections import deque
from ..exceptions.custom_exceptions import DataStructureError

T = TypeVar('T')


class TreeNode(Generic[T]):
    """
    树节点类
    每个节点可以拥有多个子节点
    """
    
    def __init__(self, data: T, parent: Optional['TreeNode[T]'] = None):
        self.data: T = data
        self.parent: Optional['TreeNode[T]'] = parent
        self.children: List['TreeNode[T]'] = []
        self._depth: int = 0 if parent is None else parent._depth + 1
    
    def add_child(self, data: T) -> 'TreeNode[T]':
        """添加子节点 - O(1)"""
        child = TreeNode(data, self)
        self.children.append(child)
        return child
    
    def remove_child(self, data: T) -> bool:
        """移除指定数据的子节点 - O(n)"""
        for i, child in enumerate(self.children):
            if child.data == data:
                self.children.pop(i)
                return True
        return False
    
    def is_leaf(self) -> bool:
        """判断是否为叶子节点 - O(1)"""
        return len(self.children) == 0
    
    def is_root(self) -> bool:
        """判断是否为根节点 - O(1)"""
        return self.parent is None
    
    def get_depth(self) -> int:
        """获取节点深度 - O(1)"""
        return self._depth
    
    def get_height(self) -> int:
        """获取以该节点为根的子树高度 - O(n)"""
        if self.is_leaf():
            return 0
        return 1 + max(child.get_height() for child in self.children)
    
    def __repr__(self) -> str:
        return f"TreeNode({self.data})"


class GeneralTree(Generic[T]):
    """
    通用树类
    支持多叉树的各种操作和递归遍历
    """
    
    def __init__(self, root_data: Optional[T] = None):
        self._root: Optional[TreeNode[T]] = None
        if root_data is not None:
            self._root = TreeNode(root_data)
        self._size: int = 1 if root_data is not None else 0
    
    # ==================== 基本属性 ====================
    
    @property
    def root(self) -> Optional[TreeNode[T]]:
        """获取根节点"""
        return self._root
    
    def is_empty(self) -> bool:
        """检查树是否为空"""
        return self._root is None
    
    def size(self) -> int:
        """返回节点数量"""
        return self._size
    
    def __len__(self) -> int:
        return self._size
    
    # ==================== 节点操作 ====================
    
    def set_root(self, data: T) -> TreeNode[T]:
        """设置根节点"""
        if self._root is not None:
            raise DataStructureError("GeneralTree", "根节点已存在")
        self._root = TreeNode(data)
        self._size = 1
        return self._root
    
    def find(self, predicate: Callable[[T], bool]) -> Optional[TreeNode[T]]:
        """查找满足条件的节点 - O(n)"""
        if self._root is None:
            return None
        return self._find_recursive(self._root, predicate)
    
    def _find_recursive(self, node: TreeNode[T], 
                        predicate: Callable[[T], bool]) -> Optional[TreeNode[T]]:
        """递归查找节点"""
        if predicate(node.data):
            return node
        
        for child in node.children:
            result = self._find_recursive(child, predicate)
            if result is not None:
                return result
        
        return None
    
    def find_all(self, predicate: Callable[[T], bool]) -> List[TreeNode[T]]:
        """查找所有满足条件的节点 - O(n)"""
        results = []
        if self._root:
            self._find_all_recursive(self._root, predicate, results)
        return results
    
    def _find_all_recursive(self, node: TreeNode[T], 
                            predicate: Callable[[T], bool],
                            results: List[TreeNode[T]]) -> None:
        """递归查找所有匹配节点"""
        if predicate(node.data):
            results.append(node)
        
        for child in node.children:
            self._find_all_recursive(child, predicate, results)
    
    # ==================== 递归遍历 ====================
    
    def preorder_traversal(self) -> Iterator[T]:
        """
        前序遍历（根-左-右）- O(n)
        使用递归实现
        """
        if self._root:
            yield from self._preorder_recursive(self._root)
    
    def _preorder_recursive(self, node: TreeNode[T]) -> Iterator[T]:
        """前序遍历递归辅助函数"""
        yield node.data
        for child in node.children:
            yield from self._preorder_recursive(child)
    
    def postorder_traversal(self) -> Iterator[T]:
        """
        后序遍历（左-右-根）- O(n)
        使用递归实现
        """
        if self._root:
            yield from self._postorder_recursive(self._root)
    
    def _postorder_recursive(self, node: TreeNode[T]) -> Iterator[T]:
        """后序遍历递归辅助函数"""
        for child in node.children:
            yield from self._postorder_recursive(child)
        yield node.data
    
    def levelorder_traversal(self) -> Iterator[T]:
        """
        层序遍历（广度优先）- O(n)
        使用队列实现
        """
        if self._root is None:
            return
        
        queue = deque([self._root])
        
        while queue:
            node = queue.popleft()
            yield node.data
            queue.extend(node.children)
    
    # ==================== 树信息 ====================
    
    def height(self) -> int:
        """获取树高度 - O(n)"""
        if self._root is None:
            return -1
        return self._root.get_height()
    
    def get_nodes_at_depth(self, depth: int) -> List[TreeNode[T]]:
        """获取指定深度的所有节点 - O(n)"""
        if self._root is None or depth < 0:
            return []
        
        result = []
        self._get_nodes_at_depth_recursive(self._root, depth, 0, result)
        return result
    
    def _get_nodes_at_depth_recursive(self, node: TreeNode[T], 
                                       target_depth: int, 
                                       current_depth: int,
                                       result: List[TreeNode[T]]) -> None:
        """递归获取指定深度节点"""
        if current_depth == target_depth:
            result.append(node)
            return
        
        for child in node.children:
            self._get_nodes_at_depth_recursive(
                child, target_depth, current_depth + 1, result
            )
    
    # ==================== 字符串表示 ====================
    
    def __repr__(self) -> str:
        return f"GeneralTree(size={self._size})"
    
    def __str__(self) -> str:
        """可视化树结构"""
        if self._root is None:
            return "GeneralTree: [空]"
        
        lines = ["GeneralTree:"]
        self._str_recursive(self._root, "", True, lines)
        return "\n".join(lines)
    
    def _str_recursive(self, node: TreeNode[T], 
                       prefix: str, 
                       is_last: bool, 
                       lines: List[str]) -> None:
        """递归构建字符串表示"""
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{node.data}")
        
        new_prefix = prefix + ("    " if is_last else "│   ")
        children = node.children
        
        for i, child in enumerate(children):
            is_last_child = (i == len(children) - 1)
            self._str_recursive(child, new_prefix, is_last_child, lines)
