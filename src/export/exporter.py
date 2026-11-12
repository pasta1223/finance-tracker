"""
数据导出模块
支持将财务数据导出为多种格式
"""

import csv
import os
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any
from abc import ABC, abstractmethod

from ..models.transaction import Transaction, TransactionType


# ==================== 抽象基类 ====================

class ExportFormat(ABC):
    """导出格式抽象基类"""
    
    @property
    @abstractmethod
    def extension(self) -> str:
        """文件扩展名"""
        pass
    
    @property
    @abstractmethod
    def mime_type(self) -> str:
        """MIME类型"""
        pass
    
    @abstractmethod
    def export(self, transactions: List[Transaction], filepath: str) -> bool:
        """导出数据"""
        pass


# ==================== CSV导出 ====================

class CSVExporter(ExportFormat):
    """
    CSV格式导出器
    时间复杂度: O(n)，n为交易记录数量
    """
    
    @property
    def extension(self) -> str:
        return ".csv"
    
    @property
    def mime_type(self) -> str:
        return "text/csv"
    
    def export(self, transactions: List[Transaction], filepath: str) -> bool:
        """导出为CSV文件"""
        try:
            # 确保目录存在
            directory = os.path.dirname(filepath)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                # 写入表头
                writer.writerow([
                    '交易ID', '日期', '时间', '类型', '分类', '金额', 
                    '账户', '描述', '创建时间', '记录人', '成员ID'
                ])
                
                # 写入数据
                for t in transactions:
                    writer.writerow([
                        t.transaction_id,
                        t.transaction_date.strftime('%Y-%m-%d'),
                        t.transaction_date.strftime('%H:%M:%S'),
                        t.transaction_type.value,
                        t.category,
                        f"{t.amount:.2f}",
                        t.account,
                        t.description or '',
                        t.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        t.author_name,
                        t.author_id
                    ])
            
            return True
        except IOError as e:
            print(f"[错误] CSV导出失败: {e}")
            return False


# ==================== 文本报表导出 ====================

class TextReportExporter(ExportFormat):
    """文本报表导出器"""
    
    @property
    def extension(self) -> str:
        return ".txt"
    
    @property
    def mime_type(self) -> str:
        return "text/plain"
    
    def export(self, transactions: List[Transaction], filepath: str) -> bool:
        """导出为文本报表"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                self._write_report(f, transactions)
            return True
        except IOError as e:
            print(f"[错误] 报表导出失败: {e}")
            return False
    
    def _write_report(self, f, transactions: List[Transaction]) -> None:
        """写入报表内容"""
        now = datetime.now()
        
        # 报表头部
        f.write("=" * 60 + "\n")
        f.write("            个人财务跟踪系统 - 财务报表\n")
        f.write("=" * 60 + "\n")
        f.write(f"生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"记录数量: {len(transactions)}\n")
        f.write("-" * 60 + "\n\n")
        
        # 统计汇总
        total_income = Decimal('0')
        total_expense = Decimal('0')
        category_stats: Dict[str, Decimal] = {}
        
        for t in transactions:
            if t.transaction_type == TransactionType.INCOME:
                total_income += t.amount
            else:
                total_expense += t.amount
                category_stats[t.category] = category_stats.get(t.category, Decimal('0')) + t.amount
        
        balance = total_income - total_expense
        
        f.write("【收支汇总】\n")
        f.write(f"  总收入: {total_income:>15,.2f}\n")
        f.write(f"  总支出: {total_expense:>15,.2f}\n")
        f.write(f"  余额:   {balance:>15,.2f}\n\n")
        
        # 支出分类统计
        if category_stats:
            f.write("【支出分类统计】\n")
            sorted_stats = sorted(category_stats.items(), key=lambda x: x[1], reverse=True)
            for cat, amount in sorted_stats:
                pct = (amount / total_expense * 100) if total_expense > 0 else 0
                bar = '█' * int(pct / 5)
                f.write(f"  {cat:<10} {amount:>12,.2f}  {pct:>5.1f}% {bar}\n")
        
        # 交易明细
        f.write("\n" + "-" * 60 + "\n")
        f.write("【交易明细】\n")
        f.write("-" * 60 + "\n")
        f.write(f"{'日期':<12} {'时间':<10} {'类型':<6} {'分类':<10} {'金额':>12}\n")
        f.write("-" * 60 + "\n")
        
        for t in sorted(transactions, key=lambda x: x.transaction_date, reverse=True):
            sign = "+" if t.transaction_type == TransactionType.INCOME else "-"
            f.write(
                f"{t.transaction_date.strftime('%Y-%m-%d'):<12} "
                f"{t.transaction_date.strftime('%H:%M:%S'):<10} "
                f"{t.transaction_type.value:<6} "
                f"{t.category:<10} "
                f"{sign}{t.amount:>11,.2f}\n"
            )
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("                       报表结束\n")
        f.write("=" * 60 + "\n")


# ==================== 导出管理器 ====================

class ExportManager:
    """
    导出管理器
    统一管理多种导出格式
    """
    
    EXPORTERS = {
        'csv': CSVExporter(),
        'report': TextReportExporter()
    }
    
    @classmethod
    def get_available_formats(cls) -> List[str]:
        """获取可用的导出格式"""
        return list(cls.EXPORTERS.keys())
    
    @classmethod
    def export(
        cls,
        transactions: List[Transaction],
        filepath: str,
        format_type: str = 'csv'
    ) -> bool:
        """
        导出数据
        
        :param transactions: 交易记录列表
        :param filepath: 导出文件路径
        :param format_type: 导出格式 ('csv', 'report')
        :return: 是否导出成功
        """
        exporter = cls.EXPORTERS.get(format_type.lower())
        if exporter is None:
            print(f"[错误] 不支持的导出格式: {format_type}")
            return False
        
        return exporter.export(transactions, filepath)
    
    @classmethod
    def export_with_auto_name(
        cls,
        transactions: List[Transaction],
        directory: str,
        format_type: str = 'csv'
    ) -> str:
        """
        自动生成文件名导出
        
        :return: 导出的文件路径
        """
        if format_type not in cls.EXPORTERS:
            raise ValueError(f"不支持的格式: {format_type}")
        
        exporter = cls.EXPORTERS[format_type]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"finance_export_{timestamp}{exporter.extension}"
        filepath = os.path.join(directory, filename)
        
        if exporter.export(transactions, filepath):
            return filepath
        return ""
