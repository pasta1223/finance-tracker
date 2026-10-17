"""
命令行参数解析模块
支持多种运行模式和命令行选项
"""

import sys
import argparse
from typing import Optional, List
from dataclasses import dataclass

from ..version import APP_VERSION


@dataclass
class CommandArgs:
    """命令行参数"""
    # 常规选项
    version: bool = False
    
    # 数据操作
    add_transaction: bool = False
    list_transactions: bool = False
    search: Optional[str] = None
    stat: bool = False
    
    # 导出
    export: Optional[str] = None
    export_format: str = 'csv'
    
    # 配置
    reset_config: bool = False
    show_config: bool = False
    
    # 其他
    quiet: bool = False
    debug: bool = False
    
    # 导出参数
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    transaction_type: Optional[str] = None


class ArgumentParser:
    """
    命令行参数解析器
    支持交互模式和命令行模式
    """
    
    PROGRAM_NAME = "finance-tracker"
    VERSION = APP_VERSION
    DESCRIPTION = "个人财务跟踪系统"
    
    def __init__(self):
        self._parser = argparse.ArgumentParser(
            prog=self.PROGRAM_NAME,
            description=self.DESCRIPTION,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
使用示例:
  %(prog)s              # 启动交互模式
  %(prog)s --add        # 添加交易记录
  %(prog)s --list       # 列出所有记录
  %(prog)s --export report.csv  # 导出数据到CSV
  %(prog)s --version    # 显示版本信息
  
帮助:
  %(prog)s --help       # 显示详细帮助
            """
        )
        self._setup_arguments()
    
    def _setup_arguments(self) -> None:
        """设置参数"""
        # 常规选项
        group = self._parser.add_argument_group('常规选项')
        group.add_argument(
            '-v', '--version',
            action='store_true',
            help='显示版本信息'
        )
        group.add_argument(
            '-q', '--quiet',
            action='store_true',
            help='安静模式（最小化输出）'
        )
        group.add_argument(
            '-d', '--debug',
            action='store_true',
            help='调试模式'
        )
        
        # 数据操作
        group = self._parser.add_argument_group('数据操作')
        group.add_argument(
            '-a', '--add',
            action='store_true',
            dest='add_transaction',
            help='添加新的交易记录（交互模式）'
        )
        group.add_argument(
            '-l', '--list',
            action='store_true',
            dest='list_transactions',
            help='列出所有交易记录'
        )
        group.add_argument(
            '-s', '--search',
            metavar='KEYWORD',
            help='搜索交易记录'
        )
        group.add_argument(
            '-S', '--stat',
            action='store_true',
            help='显示统计信息'
        )
        
        # 导出选项
        group = self._parser.add_argument_group('导出选项')
        group.add_argument(
            '-e', '--export',
            metavar='FILE',
            help='导出数据到指定文件'
        )
        group.add_argument(
            '-f', '--format',
            choices=['csv', 'report'],
            default='csv',
            dest='export_format',
            help='导出文件格式 (默认: csv)'
        )
        group.add_argument(
            '--start-date',
            metavar='DATE',
            help='导出起始日期 (YYYY-MM-DD)'
        )
        group.add_argument(
            '--end-date',
            metavar='DATE',
            help='导出结束日期 (YYYY-MM-DD)'
        )
        group.add_argument(
            '--category',
            metavar='CAT',
            help='按分类筛选'
        )
        group.add_argument(
            '--type',
            choices=['income', 'expense'],
            dest='transaction_type',
            help='按类型筛选'
        )
        
        # 配置选项
        group = self._parser.add_argument_group('配置选项')
        group.add_argument(
            '--reset-config',
            action='store_true',
            help='重置配置为默认值'
        )
        group.add_argument(
            '--show-config',
            action='store_true',
            help='显示当前配置'
        )
    
    def parse(self, args: Optional[List[str]] = None) -> CommandArgs:
        """解析命令行参数"""
        parsed = self._parser.parse_args(args)
        
        return CommandArgs(
            version=parsed.version,
            add_transaction=parsed.add_transaction,
            list_transactions=parsed.list_transactions,
            search=parsed.search,
            stat=parsed.stat,
            export=parsed.export,
            export_format=parsed.export_format,
            reset_config=parsed.reset_config,
            show_config=parsed.show_config,
            quiet=parsed.quiet,
            debug=parsed.debug,
            start_date=parsed.start_date,
            end_date=parsed.end_date,
            category=parsed.category,
            transaction_type=parsed.transaction_type
        )
    
    def print_help(self) -> None:
        """打印帮助"""
        self._parser.print_help()
    
    @staticmethod
    def print_version() -> None:
        """打印版本"""
        print(f"{ArgumentParser.PROGRAM_NAME} v{ArgumentParser.VERSION}")
        print(f"  {ArgumentParser.DESCRIPTION}")
