"""
财务记录管理器
核心业务逻辑层，管理所有财务记录的增删改查
使用组合模式集成多种数据结构
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Callable
from abc import ABC, abstractmethod

from ..models.transaction import Transaction, TransactionType
from ..models.category import Category
from ..data_structures.doubly_linked_list import DoublyLinkedList
from ..data_structures.stack import Stack
from ..data_structures.queue import Queue
from ..data_structures.binary_search_tree import BinarySearchTree
from ..data_structures.hash_table import HashTable
from ..data_structures.tree import GeneralTree
from ..exceptions.custom_exceptions import (
    ValidationError, TransactionError, NotFoundError, StorageError
)


# ==================== 抽象基类：财务记录仓库接口 ====================

class FinancialRepository(ABC):
    """财务记录仓库抽象基类（定义多态接口）"""
    
    @abstractmethod
    def add(self, transaction: Transaction) -> None:
        """添加记录"""
        pass
    
    @abstractmethod
    def remove(self, transaction_id: str) -> bool:
        """删除记录"""
        pass
    
    @abstractmethod
    def update(self, transaction_id: str, **kwargs) -> None:
        """更新记录"""
        pass
    
    @abstractmethod
    def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """根据ID查找"""
        pass
    
    @abstractmethod
    def find_all(self) -> List[Transaction]:
        """获取所有记录"""
        pass


# ==================== 组合模式：财务记录管理器 ====================

class TransactionManager(FinancialRepository):
    """
    财务记录管理器
    使用组合模式整合多种数据结构
    
    数据结构使用情况：
    - HashTable: 通过ID快速查找 O(1)
    - BST: 按金额/日期排序存储 O(log n)
    - DoublyLinkedList: 按插入顺序存储，支持双向遍历
    - Queue: 撤销操作栈（实际上是Stack）
    - GeneralTree: 分类层级结构
    
    时间复杂度分析：
    - 添加记录: O(log n) - BST插入 + HashTable更新
    - 删除记录: O(log n) + O(1) - BST删除 + HashTable删除
    - 查找（按ID）: O(1) - HashTable查找
    - 查找（按金额范围）: O(log n + k) - BST范围查询
    - 按日期排序: O(n log n) - BST中序遍历
    """
    
    def __init__(self):
        # 主存储：HashTable（按ID索引）- O(1) 查找
        self._by_id: HashTable[Transaction] = HashTable()
        
        # 排序存储：BST（按金额）- O(log n) 插入和范围查询
        self._by_amount: BinarySearchTree[Transaction] = BinarySearchTree(
            key_func=lambda t: float(t.amount)
        )
        
        # BST（按日期）- 用于按时间排序
        self._by_date: BinarySearchTree[Transaction] = BinarySearchTree(
            key_func=lambda t: t.transaction_date.timestamp()
        )
        
        # 双向链表：按插入顺序存储
        self._by_insertion_order: DoublyLinkedList[Transaction] = DoublyLinkedList()
        
        # 分类树：组织分类层级
        self._category_tree: GeneralTree[str] = GeneralTree("根分类")
        
        # 操作历史（用于撤销）- 使用Stack实现
        self._undo_stack: Stack[Dict] = Stack()
        self._redo_stack: Stack[Dict] = Stack()
        
        # 统计数据
        self._total_income: Decimal = Decimal('0')
        self._total_expense: Decimal = Decimal('0')
    
    # ==================== FinancialRepository 实现 ====================
    
    def add(self, transaction: Transaction) -> None:
        """添加交易记录"""
        if transaction is None:
            raise ValidationError("transaction", "交易记录不能为空")
        
        # 检查ID是否已存在
        if self._by_id.contains_key(transaction.transaction_id):
            raise TransactionError(
                transaction.transaction_id,
                "交易ID已存在"
            )
        
        # 存储到各个数据结构
        self._by_id.put(transaction.transaction_id, transaction)
        self._by_amount.insert(transaction)
        self._by_date.insert(transaction)
        self._by_insertion_order.append(transaction)
        
        # 更新统计
        if transaction.transaction_type == TransactionType.INCOME:
            self._total_income += transaction.amount
        else:
            self._total_expense += transaction.amount
        
        # 记录操作（用于撤销）
        self._undo_stack.push({
            "action": "add",
            "transaction": transaction
        })
        self._redo_stack.clear()
    
    def remove(self, transaction_id: str) -> bool:
        """删除交易记录"""
        transaction = self._by_id.get(transaction_id)
        if transaction is None:
            raise NotFoundError("Transaction", transaction_id)
        
        # 计算用于 BST 删除的键
        amount_key = float(transaction.amount)
        date_key = transaction.transaction_date.timestamp()
        
        # 从各数据结构移除
        self._by_id.remove(transaction_id)
        self._by_amount.delete(amount_key)  # 从金额BST删除
        self._by_date.delete(date_key)      # 从日期BST删除
        self._by_insertion_order.remove(transaction)
        
        # 更新统计
        if transaction.transaction_type == TransactionType.INCOME:
            self._total_income -= transaction.amount
        else:
            self._total_expense -= transaction.amount
        
        # 记录操作
        self._undo_stack.push({
            "action": "remove",
            "transaction": transaction
        })
        self._redo_stack.clear()
        
        return True
    
    def update(self, transaction_id: str, **kwargs) -> None:
        """更新交易记录"""
        transaction = self.find_by_id(transaction_id)
        if transaction is None:
            raise NotFoundError("Transaction", transaction_id)
        
        old_values = {}
        for key, value in kwargs.items():
            if hasattr(transaction, key):
                old_values[key] = getattr(transaction, key)
                try:
                    setattr(transaction, key, value)
                except ValidationError as e:
                    # 回滚已修改的属性
                    for k, v in old_values.items():
                        setattr(transaction, k, v)
                    raise
        
        # 记录操作
        self._undo_stack.push({
            "action": "update",
            "transaction_id": transaction_id,
            "old_values": old_values
        })
        self._redo_stack.clear()
    
    def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """根据ID查找 - O(1)"""
        return self._by_id.get(transaction_id)
    
    def find_all(self) -> List[Transaction]:
        """获取所有记录（按插入顺序）"""
        return self._by_insertion_order.to_list()
    
    # ==================== 高级查询方法 ====================
    
    def find_by_amount_range(
        self, 
        min_amount: Decimal, 
        max_amount: Decimal
    ) -> List[Transaction]:
        """
        按金额范围查找 - O(log n + k)
        k 为结果数量
        """
        return self._by_amount.range_query(
            float(min_amount), 
            float(max_amount)
        )
    
    def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Transaction]:
        """按日期范围查找 - O(n)"""
        results = []
        for transaction in self._by_insertion_order:
            if start_date <= transaction.transaction_date <= end_date:
                results.append(transaction)
        return results
    
    def find_by_category(self, category: str) -> List[Transaction]:
        """按分类查找 - O(n)"""
        return self._by_insertion_order.find_all(
            lambda t: t.category == category
        )
    
    def find_by_type(self, transaction_type: TransactionType) -> List[Transaction]:
        """按类型查找 - O(n)"""
        return self._by_insertion_order.find_all(
            lambda t: t.transaction_type == transaction_type
        )
    
    def search(self, predicate: Callable[[Transaction], bool]) -> List[Transaction]:
        """自定义条件搜索 - O(n)"""
        return self._by_insertion_order.find_all(predicate)
    
    # ==================== 排序方法（使用递归树遍历） ====================
    
    def get_sorted_by_amount(self, descending: bool = False) -> List[Transaction]:
        """
        按金额排序
        使用BST中序遍历 - O(n)
        """
        transactions = self._by_amount.to_list()
        return sorted(transactions, key=lambda t: t.amount, reverse=descending)
    
    def get_sorted_by_date(self, descending: bool = False) -> List[Transaction]:
        """
        按日期排序
        使用BST中序遍历 - O(n)
        """
        transactions = self.find_all()
        return sorted(
            transactions, 
            key=lambda t: t.transaction_date, 
            reverse=descending
        )
    
    def get_recent_transactions(self, count: int = 10) -> List[Transaction]:
        """获取最近的N条记录"""
        all_transactions = self.get_sorted_by_date(descending=True)
        return all_transactions[:count]
    
    # ==================== 统计方法 ====================
    
    def get_total_income(self) -> Decimal:
        """获取总收入"""
        return self._total_income
    
    def get_total_expense(self) -> Decimal:
        """获取总支出"""
        return self._total_expense
    
    def get_balance(self) -> Decimal:
        """获取余额"""
        return self._total_income - self._total_expense
    
    def get_statistics_by_category(self) -> Dict[str, Decimal]:
        """按分类统计支出"""
        stats: Dict[str, Decimal] = {}
        for transaction in self._by_insertion_order:
            if transaction.transaction_type == TransactionType.EXPENSE:
                category = transaction.category
                stats[category] = stats.get(category, Decimal('0')) + transaction.amount
        return stats
    
    def get_monthly_statistics(self, year: int, month: int) -> Dict:
        """获取月度统计"""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        transactions = self.find_by_date_range(start_date, end_date)
        
        income = sum(
            t.amount for t in transactions 
            if t.transaction_type == TransactionType.INCOME
        )
        expense = sum(
            t.amount for t in transactions 
            if t.transaction_type == TransactionType.EXPENSE
        )
        
        return {
            "year": year,
            "month": month,
            "income": income,
            "expense": expense,
            "balance": income - expense,
            "transaction_count": len(transactions)
        }
    
    # ==================== 撤销/重做 ====================
    
    def undo(self) -> bool:
        """
        撤销上一个操作
        使用栈实现 - O(1)
        """
        if self._undo_stack.is_empty():
            return False
        
        action = self._undo_stack.pop()
        
        if action["action"] == "add":
            # 撤销添加 = 删除（从所有数据结构中移除）
            transaction = action["transaction"]
            amount_key = float(transaction.amount)
            date_key = transaction.transaction_date.timestamp()
            
            self._by_id.remove(transaction.transaction_id)
            self._by_amount.delete(amount_key)
            self._by_date.delete(date_key)
            self._by_insertion_order.remove(transaction)
            
            if transaction.transaction_type == TransactionType.INCOME:
                self._total_income -= transaction.amount
            else:
                self._total_expense -= transaction.amount
        
        elif action["action"] == "remove":
            # 撤销删除 = 重新添加（恢复到所有数据结构）
            transaction = action["transaction"]
            self._by_id.put(transaction.transaction_id, transaction)
            self._by_amount.insert(transaction)
            self._by_date.insert(transaction)
            self._by_insertion_order.append(transaction)
            
            if transaction.transaction_type == TransactionType.INCOME:
                self._total_income += transaction.amount
            else:
                self._total_expense += transaction.amount
        
        elif action["action"] == "update":
            # 撤销更新 = 恢复旧值
            transaction = self._by_id.get(action["transaction_id"])
            for key, value in action["old_values"].items():
                setattr(transaction, key, value)
        
        self._redo_stack.push(action)
        return True
    
    def redo(self) -> bool:
        """重做上一个撤销的操作"""
        if self._redo_stack.is_empty():
            return False
        
        action = self._redo_stack.pop()
        
        if action["action"] == "add":
            # 重做添加 = 重新添加（添加到所有数据结构）
            transaction = action["transaction"]
            self._by_id.put(transaction.transaction_id, transaction)
            self._by_amount.insert(transaction)
            self._by_date.insert(transaction)
            self._by_insertion_order.append(transaction)
            
            if transaction.transaction_type == TransactionType.INCOME:
                self._total_income += transaction.amount
            else:
                self._total_expense += transaction.amount
        
        elif action["action"] == "remove":
            # 重做删除 = 重新删除（从所有数据结构移除）
            transaction = action["transaction"]
            amount_key = float(transaction.amount)
            date_key = transaction.transaction_date.timestamp()
            
            self._by_id.remove(transaction.transaction_id)
            self._by_amount.delete(amount_key)
            self._by_date.delete(date_key)
            self._by_insertion_order.remove(transaction)
            
            if transaction.transaction_type == TransactionType.INCOME:
                self._total_income -= transaction.amount
            else:
                self._total_expense -= transaction.amount
        
        elif action["action"] == "update":
            transaction = self._by_id.get(action["transaction_id"])
            # 应用之前更新的值
            for key, value in action.get("new_values", {}).items():
                setattr(transaction, key, value)
        
        self._undo_stack.push(action)
        return True
    
    def can_undo(self) -> bool:
        """检查是否可以撤销"""
        return not self._undo_stack.is_empty()
    
    def can_redo(self) -> bool:
        """检查是否可以重做"""
        return not self._redo_stack.is_empty()
    
    def get_last_action(self) -> Optional[Dict]:
        """获取最后一个操作（不弹出）"""
        if self._undo_stack.is_empty():
            return None
        return self._undo_stack.peek()
    
    def get_last_redo_action(self) -> Optional[Dict]:
        """获取最后一个可重做的操作（不弹出）"""
        if self._redo_stack.is_empty():
            return None
        return self._redo_stack.peek()
    
    # ==================== 分类管理（使用树结构） ====================
    
    def add_category(self, name: str, parent_path: Optional[str] = None) -> Category:
        """添加分类（支持层级结构）"""
        category = Category(name, "expense" if "支出" not in name else "income")
        
        if parent_path:
            parent_node = self._category_tree.find(lambda n: n == parent_path)
            if parent_node:
                parent_node.add_child(name)
            else:
                self._category_tree.root.add_child(name)
        else:
            self._category_tree.root.add_child(name)
        
        return category
    
    def get_all_categories(self) -> List[str]:
        """获取所有分类"""
        return list(self._category_tree.preorder_traversal())
    
    # ==================== 属性 ====================
    
    @property
    def transaction_count(self) -> int:
        """交易记录总数"""
        return len(self._by_id)
    
    @property
    def is_empty(self) -> bool:
        """是否为空"""
        return self._by_id.is_empty()
    
    # ==================== 序列化 ====================
    
    def to_dict(self) -> dict:
        """转换为字典（用于保存）"""
        return {
            "transactions": [t.to_dict() for t in self._by_insertion_order],
            "statistics": {
                "total_income": str(self._total_income),
                "total_expense": str(self._total_expense)
            }
        }
    
    def from_dict(self, data: dict) -> None:
        """从字典加载（用于恢复）"""
        # Reinitialize every index so repeated reloads cannot leave stale BST
        # entries or persisted actions in the undo/redo history.
        self.__init__()
        
        for t_data in data.get("transactions", []):
            transaction = Transaction.from_dict(t_data)
            self.add(transaction)
        
        stats = data.get("statistics", {})
        self._total_income = Decimal(stats.get("total_income", "0"))
        self._total_expense = Decimal(stats.get("total_expense", "0"))
        self._undo_stack.clear()
        self._redo_stack.clear()
    
    def __len__(self) -> int:
        return self.transaction_count
    
    def __repr__(self) -> str:
        return f"TransactionManager(count={self.transaction_count}, balance={self.get_balance()})"
