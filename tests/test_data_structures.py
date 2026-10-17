"""
数据结构和模型单元测试
"""

import unittest
import sys
import os
from datetime import datetime
from decimal import Decimal

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.data_structures.doubly_linked_list import DoublyLinkedList, Node
from src.data_structures.stack import Stack
from src.data_structures.queue import Queue
from src.data_structures.binary_search_tree import BinarySearchTree, BSTNode
from src.data_structures.hash_table import HashTable
from src.data_structures.tree import GeneralTree, TreeNode
from src.models.transaction import Transaction, TransactionType
from src.models.category import Category
from src.exceptions.custom_exceptions import (
    ValidationError, DataStructureError, FinanceTrackerError
)


class TestDoublyLinkedList(unittest.TestCase):
    """双向链表测试"""
    
    def setUp(self):
        self.dll = DoublyLinkedList()
    
    def test_append_and_iterate(self):
        """测试追加和迭代"""
        self.dll.append(1)
        self.dll.append(2)
        self.dll.append(3)
        self.assertEqual(list(self.dll), [1, 2, 3])
    
    def test_prepend(self):
        """测试头部插入"""
        self.dll.append(2)
        self.dll.append(3)
        self.dll.prepend(1)
        self.assertEqual(list(self.dll), [1, 2, 3])
    
    def test_remove(self):
        """测试删除"""
        self.dll.append(1)
        self.dll.append(2)
        self.dll.append(3)
        self.dll.remove(2)
        self.assertEqual(list(self.dll), [1, 3])
    
    def test_pop(self):
        """测试尾部弹出"""
        self.dll.append(1)
        self.dll.append(2)
        self.assertEqual(self.dll.pop(), 2)
        self.assertEqual(list(self.dll), [1])
    
    def test_is_empty(self):
        """测试空判断"""
        self.assertTrue(self.dll.is_empty())
        self.dll.append(1)
        self.assertFalse(self.dll.is_empty())


class TestStack(unittest.TestCase):
    """栈测试"""
    
    def setUp(self):
        self.stack = Stack()
    
    def test_push_pop(self):
        """测试入栈出栈"""
        self.stack.push(1)
        self.stack.push(2)
        self.assertEqual(self.stack.pop(), 2)
        self.assertEqual(self.stack.pop(), 1)
    
    def test_peek(self):
        """测试查看栈顶"""
        self.stack.push(1)
        self.stack.push(2)
        self.assertEqual(self.stack.peek(), 2)
        self.assertEqual(len(self.stack), 2)
    
    def test_empty_stack_error(self):
        """测试空栈错误"""
        with self.assertRaises(DataStructureError):
            self.stack.pop()


class TestQueue(unittest.TestCase):
    """队列测试"""
    
    def setUp(self):
        self.queue = Queue()
    
    def test_enqueue_dequeue(self):
        """测试入队出队"""
        self.queue.enqueue(1)
        self.queue.enqueue(2)
        self.assertEqual(self.queue.dequeue(), 1)
        self.assertEqual(self.queue.dequeue(), 2)
    
    def test_fifo_order(self):
        """测试FIFO顺序"""
        for i in range(5):
            self.queue.enqueue(i)
        result = []
        while not self.queue.is_empty():
            result.append(self.queue.dequeue())
        self.assertEqual(result, [0, 1, 2, 3, 4])


class TestBinarySearchTree(unittest.TestCase):
    """二叉搜索树测试"""
    
    def setUp(self):
        self.bst = BinarySearchTree(key_func=lambda x: x)
    
    def test_insert(self):
        """测试插入"""
        self.bst.insert(5)
        self.bst.insert(3)
        self.bst.insert(7)
        self.assertEqual(self.bst.size(), 3)
    
    def test_find(self):
        """测试查找"""
        self.bst.insert(5)
        self.bst.insert(3)
        self.bst.insert(7)
        self.assertEqual(self.bst.find(5), 5)
        self.assertIsNone(self.bst.find(99))
    
    def test_inorder_traversal(self):
        """测试中序遍历（递归）"""
        for val in [5, 3, 7, 1, 4, 6, 8]:
            self.bst.insert(val)
        result = list(self.bst.inorder_traversal())
        self.assertEqual(result, [1, 3, 4, 5, 6, 7, 8])


class TestHashTable(unittest.TestCase):
    """哈希表测试"""
    
    def setUp(self):
        self.ht = HashTable()
    
    def test_put_get(self):
        """测试插入和获取"""
        self.ht.put("key1", "value1")
        self.ht.put("key2", "value2")
        self.assertEqual(self.ht.get("key1"), "value1")
    
    def test_remove(self):
        """测试删除"""
        self.ht.put("key1", "value1")
        self.ht.remove("key1")
        self.assertIsNone(self.ht.get("key1"))


class TestTransaction(unittest.TestCase):
    """交易记录测试"""
    
    def test_create_transaction(self):
        """测试创建交易"""
        t = Transaction(
            amount=Decimal("100.00"),
            transaction_type=TransactionType.INCOME,
            category="工资"
        )
        self.assertEqual(t.amount, Decimal("100.00"))
    
    def test_validation_amount(self):
        """测试金额验证"""
        with self.assertRaises(ValidationError):
            Transaction(
                amount=Decimal("-10"),
                transaction_type=TransactionType.EXPENSE,
                category="测试"
            )
    
    def test_to_dict_from_dict(self):
        """测试序列化/反序列化"""
        t1 = Transaction(
            amount=Decimal("100.50"),
            transaction_type=TransactionType.INCOME,
            category="奖金"
        )
        data = t1.to_dict()
        t2 = Transaction.from_dict(data)
        self.assertEqual(t1.amount, t2.amount)


class TestCategory(unittest.TestCase):
    """分类测试"""
    
    def test_create_category(self):
        """测试创建分类"""
        cat = Category("餐饮", "expense")
        self.assertEqual(cat.name, "餐饮")
        self.assertTrue(cat.is_root)
    
    def test_hierarchy(self):
        """测试层级结构"""
        parent = Category("餐饮", "expense")
        child = Category("早餐", "expense", parent=parent)
        self.assertEqual(child.full_path, "餐饮 > 早餐")


class TestCustomExceptions(unittest.TestCase):
    """自定义异常测试"""
    
    def test_exception_hierarchy(self):
        """测试异常层次"""
        self.assertTrue(issubclass(ValidationError, FinanceTrackerError))
        self.assertTrue(issubclass(DataStructureError, FinanceTrackerError))


if __name__ == '__main__':
    unittest.main()
