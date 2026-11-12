"""
CLI用户界面模块
提供命令行交互界面
支持完整的财务管理功能
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

# Support IDEs and terminals that execute this internal file directly.  The
# canonical entry point remains main.py so argument parsing, logging, encoding,
# and SQLite path setup stay identical for every CLI launch method.
if __name__ == "__main__" and not __package__:
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from main import main as run_cli

    raise SystemExit(run_cli())

from ..models.transaction import Transaction, TransactionType
from ..export.exporter import ExportManager
from ..exceptions.custom_exceptions import FinanceTrackerError, ValidationError, NotFoundError
from ..version import APP_VERSION
from .cli_login import authenticate_cli
from ..services.workspaces import PROFILES
from ..services.auth_service import AuthenticationError
from ..core.logger import Logger


class FinanceCLI:
    """
    财务跟踪系统命令行界面
    提供用户交互接口
    """
    
    def __init__(self, config=None, logger=None, state=None, quiet=None):
        self._config = config
        self._logger = logger
        self._quiet = bool(
            getattr(config, "quiet", False) if quiet is None else quiet
        )
        
        # GUI and CLI share the same state serialization and SQLite backend.
        self._state = state if state is not None else authenticate_cli()
        if self._state.session and isinstance(logger, Logger):
            # Financial diagnostics belong beside the current ledger, never
            # in the shared startup log. A separate logger name avoids reuse.
            self._logger = Logger(
                name=f"FinanceLedger_{self._state.session.workspace_id}",
                log_file=str(Path(self._state.storage_path).with_suffix(".log")),
                level=logger._level,
            )
            self._logger._logger.propagate = False
        self._storage = self._state.storage
        self._manager = self._state.transaction_manager
        self._budget_manager = self._state.budget_manager
        
        # 加载已有数据
        self._load_data()
        
        # 默认分类
        self._default_categories = {
            "income": ["工资", "奖金", "投资收益", "兼职", "其他收入"],
            "expense": ["餐饮", "交通", "购物", "住房", "医疗", "教育", "娱乐", "通讯", "其他支出"]
        }
        if self._state.session:
            profile = PROFILES[self._state.session.kind]
            self._default_categories = {"income": profile["income_categories"], "expense": profile["expense_categories"]}
        
        # 导出管理器
        self._export_manager = ExportManager()
    
    def _log(self, message: str, level: str = "info") -> None:
        """日志记录"""
        if self._logger:
            getattr(self._logger, level)(message)
    
    def _load_data(self) -> None:
        """Load transactions and budgets through the shared application state."""
        if self._state.load():
            self._log(f"已从 {self._state.storage_path} 加载数据")

            if not self._quiet:
                print(f"[系统] 已从 {self._state.storage_path} 加载数据")
                print(f"[系统] 共加载 {self._manager.transaction_count} 条交易记录\n")
    
    def _save_data(self) -> bool:
        """Save transactions and budgets together through shared SQLite state."""
        success = self._state.save()
        if success:
            self._log("数据已保存")
        else:
            error = self._state.last_error or "未知错误"
            reloaded = self._state.reload()
            recovery = (
                "已重新加载数据库中的最新状态"
                if reloaded
                else "无法重新加载数据库，当前改动仍只存在于内存中"
            )
            self._log(f"保存数据失败: {error}; {recovery}", "error")
            print(f"[错误] 保存数据失败: {error}；{recovery}")
        return success
    
    def run(self) -> None:
        """运行主循环"""
        self._print_welcome()
        
        while True:
            try:
                self._state._authorize()
                self._print_menu()
                choice = input("\n请选择操作 [1-9]: ").strip()
                
                if choice == '1':
                    self._add_transaction()
                elif choice == '2':
                    self._delete_transaction()
                elif choice == '3':
                    self._update_transaction()
                elif choice == '4':
                    self._search_transactions()
                elif choice == '5':
                    self._view_statistics()
                elif choice == '6':
                    self._list_transactions()
                elif choice == '7':
                    self._manage_budget()
                elif choice == '8':
                    self._export_menu()
                elif choice == '9':
                    self._exit_program()
                    break
                else:
                    print("[提示] 无效选择，请重新输入")
                    
            except KeyboardInterrupt:
                print("\n\n[提示] 按 Ctrl+C 退出程序")
                self._exit_program()
                break
            except AuthenticationError as e:
                print(f"[错误] {e.message}")
                break
            except FinanceTrackerError as e:
                print(f"[错误] {e.message}")
            except Exception as e:
                self._log(f"未知错误: {e}", "error")
                print(f"[错误] 发生未知错误: {e}")
    
    def _print_welcome(self) -> None:
        """打印欢迎信息"""
        print("\n" + "=" * 50)
        print("        欢迎使用个人财务跟踪系统")
        print(f"        版本 {APP_VERSION}")
        print("=" * 50)
        print(f"        当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 50)
    
    def _print_menu(self) -> None:
        """打印菜单"""
        balance = self._manager.get_balance()
        
        print(f"\n┌{'─' * 48}┐")
        print(f"│ 当前余额: {balance:>32,.2f} │")
        print(f"│ 记录总数: {str(self._manager.transaction_count):>32} │")
        print(f"├{'─' * 48}┤")
        print(f"│ {'1. 添加交易记录':<44} │")
        print(f"│ {'2. 删除交易记录':<44} │")
        print(f"│ {'3. 更新交易记录':<44} │")
        print(f"│ {'4. 搜索/查询记录':<44} │")
        print(f"│ {'5. 查看统计信息':<44} │")
        print(f"│ {'6. 列出所有记录':<44} │")
        print(f"│ {'7. 预算管理':<44} │")
        print(f"│ {'8. 数据导出':<44} │")
        print(f"│ {'9. 退出系统':<44} │")
        print(f"└{'─' * 48}┘")
    
    # ==================== 交易操作 ====================
    
    def _add_transaction(self) -> None:
        """添加交易记录"""
        print("\n--- 添加交易记录 ---")
        
        # 选择类型
        print("交易类型:")
        print("1. 收入")
        print("2. 支出")
        
        type_choice = self._safe_input("请选择类型 [1/2]: ", default="1")
        trans_type = TransactionType.EXPENSE if type_choice == "2" else TransactionType.INCOME
        
        # 选择分类
        categories = self._default_categories[
            "income" if trans_type == TransactionType.INCOME else "expense"
        ]
        print(f"\n可选分类:")
        for i, cat in enumerate(categories, 1):
            print(f"  {i}. {cat}")
        
        cat_choice = self._safe_input(f"\n选择分类 [1-{len(categories)}]: ", default="1")
        try:
            cat_index = int(cat_choice) - 1
            category = categories[cat_index] if 0 <= cat_index < len(categories) else categories[0]
        except ValueError:
            category = categories[0]
        
        # 输入金额
        amount_str = self._safe_input("\n金额: ", validator=self._validate_amount)
        amount = Decimal(amount_str)
        
        # 输入描述
        description = self._safe_input("描述 (可选): ")
        
        # 输入账户
        account = self._safe_input("账户 (默认: 默认账户): ", default="默认账户")
        
        # 确认创建
        print(f"\n确认信息:")
        print(f"  类型: {trans_type.value}")
        print(f"  分类: {category}")
        print(f"  金额: {amount:,.2f}")
        print(f"  描述: {description or '无'}")
        print(f"  账户: {account}")
        
        confirm = self._safe_input("\n确认添加? [y/N]: ", default="n")
        if confirm.lower() == 'y':
            transaction = Transaction(
                amount=amount,
                transaction_type=trans_type,
                category=category,
                description=description,
                account=account
            )
            
            self._manager.add(transaction)
            self._log(f"添加交易: ID={transaction.transaction_id}, 金额={amount}", "info")
            
            # 更新预算支出
            if trans_type == TransactionType.EXPENSE:
                now = datetime.now()
                self._budget_manager.add_category_spending(
                    category, now.year, now.month, amount
                )
                
                # 检查预算警告
                monthly_expense = self._manager.get_total_expense()
                alerts = self._budget_manager.check_budget_alerts(
                    now.year, now.month, monthly_expense
                )
                for alert in alerts:
                    print(alert)
            
            if self._save_data():
                print(f"\n[成功] 已添加交易记录 (ID: {transaction.transaction_id})")
        else:
            print("\n[提示] 已取消添加")
    
    def _delete_transaction(self) -> None:
        """删除交易记录"""
        print("\n--- 删除交易记录 ---")
        
        if self._manager.is_empty:
            print("[提示] 暂无交易记录")
            return
        
        self._display_recent_transactions(5)
        
        transaction_id = input("\n请输入要删除的交易ID (或按回车取消): ").strip()
        
        if not transaction_id:
            print("[提示] 已取消删除")
            return
        
        transaction = self._manager.find_by_id(transaction_id)
        if transaction is None:
            print(f"[错误] 未找到ID为 {transaction_id} 的记录")
            return
        
        print(f"\n确认删除以下记录?")
        print(f"  {transaction}")
        
        confirm = self._safe_input("\n确认删除? [y/N]: ", default="n")
        if confirm.lower() == 'y':
            self._manager.remove(transaction_id)
            self._log(f"删除交易: ID={transaction_id}", "info")
            if self._save_data():
                print("[成功] 已删除交易记录")
        else:
            print("[提示] 已取消删除")
    
    def _update_transaction(self) -> None:
        """更新交易记录"""
        print("\n--- 更新交易记录 ---")
        
        if self._manager.is_empty:
            print("[提示] 暂无交易记录")
            return
        
        self._display_recent_transactions(5)
        
        transaction_id = input("\n请输入要更新的交易ID (或按回车取消): ").strip()
        
        if not transaction_id:
            print("[提示] 已取消更新")
            return
        
        transaction = self._manager.find_by_id(transaction_id)
        if transaction is None:
            print(f"[错误] 未找到ID为 {transaction_id} 的记录")
            return
        
        print(f"\n当前记录: {transaction}")
        print("\n可更新的字段: amount, description, account")
        
        updates = {}
        
        new_amount = self._safe_input(f"新金额 (当前: {transaction.amount}, 跳过请按回车): ")
        if new_amount:
            try:
                updates['amount'] = Decimal(self._validate_amount(new_amount))
            except ValueError as e:
                print(f"[错误] 无效的金额格式: {e}")
                return
        
        new_desc = input(f"新描述 (当前: {transaction.description}, 跳过请按回车): ").strip()
        if new_desc:
            updates['description'] = new_desc
        
        new_account = input(f"新账户 (当前: {transaction.account}, 跳过请按回车): ").strip()
        if new_account:
            updates['account'] = new_account
        
        if not updates:
            print("[提示] 未做任何更改")
            return
        
        try:
            self._manager.update(transaction_id, **updates)
            self._log(f"更新交易: ID={transaction_id}, 字段={list(updates.keys())}", "info")
            if self._save_data():
                print("[成功] 已更新交易记录")
        except ValidationError as e:
            print(f"[错误] 更新失败: {e.message}")
    
    # ==================== 查询功能 ====================
    
    def _search_transactions(self) -> None:
        """搜索交易记录"""
        print("\n--- 搜索/查询记录 ---")
        print("1. 按分类查询")
        print("2. 按类型查询 (收入/支出)")
        print("3. 按金额范围查询")
        print("4. 按日期范围查询")
        print("5. 显示最近记录")
        
        choice = self._safe_input("\n请选择查询方式 [1-5]: ", default="5")
        
        if choice == '1':
            self._search_by_category()
        elif choice == '2':
            self._search_by_type()
        elif choice == '3':
            self._search_by_amount_range()
        elif choice == '4':
            self._search_by_date_range()
        else:
            self._display_recent_transactions(10)
    
    def _search_by_category(self) -> None:
        """按分类搜索"""
        print("\n可选分类:")
        all_cats = self._default_categories["income"] + self._default_categories["expense"]
        for i, cat in enumerate(all_cats, 1):
            print(f"  {i}. {cat}")
        
        cat_choice = self._safe_input(f"\n选择分类 [1-{len(all_cats)}]: ", default="1")
        try:
            cat_index = int(cat_choice) - 1
            category = all_cats[cat_index] if 0 <= cat_index < len(all_cats) else all_cats[0]
        except ValueError:
            category = all_cats[0]
        
        results = self._manager.find_by_category(category)
        self._display_search_results(results, f"分类 '{category}' 的记录")
    
    def _search_by_type(self) -> None:
        """按类型搜索"""
        print("\n1. 收入")
        print("2. 支出")
        choice = self._safe_input("选择类型 [1/2]: ", default="1")
        
        trans_type = TransactionType.INCOME if choice == "1" else TransactionType.EXPENSE
        results = self._manager.find_by_type(trans_type)
        self._display_search_results(results, f"{trans_type.value} 记录")
    
    def _search_by_amount_range(self) -> None:
        """按金额范围搜索"""
        min_str = self._safe_input("最小金额: ", validator=self._validate_amount)
        max_str = self._safe_input("最大金额: ", validator=self._validate_amount)
        
        min_amount = Decimal(min_str)
        max_amount = Decimal(max_str)
        
        results = self._manager.find_by_amount_range(min_amount, max_amount)
        self._display_search_results(results, f"金额 {min_amount:,.2f} - {max_amount:,.2f} 的记录")
    
    def _search_by_date_range(self) -> None:
        """按日期范围搜索"""
        start_str = self._safe_input("开始日期 (YYYY-MM-DD): ", validator=self._validate_date)
        end_str = self._safe_input("结束日期 (YYYY-MM-DD): ", validator=self._validate_date)
        
        start_date = datetime.strptime(start_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_str, "%Y-%m-%d")
        end_date = end_date.replace(hour=23, minute=59, second=59)
        
        results = self._manager.find_by_date_range(start_date, end_date)
        self._display_search_results(results, f"{start_str} 至 {end_str} 的记录")
    
    def _display_search_results(self, results: list, title: str) -> None:
        """显示搜索结果"""
        print(f"\n--- {title} ---")
        print(f"共找到 {len(results)} 条记录:\n")
        
        if not results:
            print("[提示] 未找到匹配的记录")
            return
        
        for t in results:
            print(f"  {t}")
    
    # ==================== 统计功能 ====================
    
    def _view_statistics(self) -> None:
        """查看统计信息"""
        print("\n" + "=" * 50)
        print("                    统计信息")
        print("=" * 50)
        
        # 基本统计
        income = self._manager.get_total_income()
        expense = self._manager.get_total_expense()
        balance = self._manager.get_balance()
        
        print(f"\n【收支概况】")
        print(f"  总收入:   {income:>15,.2f}")
        print(f"  总支出:   {expense:>15,.2f}")
        print(f"  余额:     {balance:>15,.2f}")
        
        # 按分类统计
        print(f"\n【支出分类统计】")
        category_stats = self._manager.get_statistics_by_category()
        
        if category_stats:
            sorted_stats = sorted(
                category_stats.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            for cat, amount in sorted_stats:
                percentage = (amount / expense * 100) if expense > 0 else 0
                bar = '█' * int(percentage / 5)
                print(f"  {cat:<10} {amount:>12,.2f}  {percentage:>5.1f}% {bar}")
        else:
            print("  暂无支出记录")
        
        # 月度统计
        now = datetime.now()
        monthly = self._manager.get_monthly_statistics(now.year, now.month)
        
        print(f"\n【本月 ({now.year}年{now.month}月) 统计】")
        print(f"  收入: {monthly['income']:>12,.2f}")
        print(f"  支出: {monthly['expense']:>12,.2f}")
        print(f"  交易笔数: {monthly['transaction_count']}")
        
        # 预算状态
        budget_summary = self._budget_manager.get_budget_summary(now.year, now.month)
        if budget_summary['monthly_budget'] > 0 or budget_summary['category_count'] > 0:
            print(f"\n【预算状态】")
            print(f"  月度预算: {budget_summary['monthly_budget']:,.2f}")
            print(f"  分类预算数: {budget_summary['category_count']}")
            if budget_summary['exceeded_count'] > 0:
                print(f"  ⚠️ 超支分类: {budget_summary['exceeded_count']}")
            if budget_summary['warning_count'] > 0:
                print(f"  ⚠️ 警告分类: {budget_summary['warning_count']}")
        
        print("\n" + "=" * 50)
    
    # ==================== 列表功能 ====================
    
    def _list_transactions(self) -> None:
        """列出所有交易记录"""
        print("\n--- 所有交易记录 ---")
        
        if self._manager.is_empty:
            print("[提示] 暂无交易记录")
            return
        
        transactions = self._manager.get_sorted_by_date(descending=True)
        
        print(f"共 {len(transactions)} 条记录:\n")
        print(f"{'日期':<12} {'类型':<6} {'分类':<10} {'金额':>12}  描述")
        print("-" * 70)
        
        for t in transactions:
            sign = "+" if t.transaction_type == TransactionType.INCOME else "-"
            print(
                f"{t.transaction_date.strftime('%Y-%m-%d'):<12} "
                f"{t.transaction_type.value:<6} "
                f"{t.category:<10} "
                f"{sign}{t.amount:>10,.2f}  "
                f"{t.description or ''}"
            )
    
    def _display_recent_transactions(self, count: int) -> None:
        """显示最近的交易记录"""
        recent = self._manager.get_recent_transactions(count)
        
        if not recent:
            print("[提示] 暂无交易记录")
            return
        
        print(f"\n最近 {len(recent)} 条记录:")
        print(f"{'ID':<10} {'日期':<12} {'类型':<6} {'金额':>12}")
        print("-" * 50)
        
        for t in recent:
            sign = "+" if t.transaction_type == TransactionType.INCOME else "-"
            print(
                f"{t.transaction_id:<10} "
                f"{t.transaction_date.strftime('%Y-%m-%d'):<12} "
                f"{t.transaction_type.value:<6} "
                f"{sign}{t.amount:>10,.2f}"
            )
    
    # ==================== 预算管理 ====================
    
    def _manage_budget(self) -> None:
        """预算管理菜单"""
        print("\n--- 预算管理 ---")
        print("1. 设置月度总预算")
        print("2. 设置分类预算")
        print("3. 查看预算状态")
        print("4. 重置预算")
        
        choice = self._safe_input("\n请选择 [1-4]: ", default="3")
        
        if choice == '1':
            self._set_monthly_budget()
        elif choice == '2':
            self._set_category_budget()
        elif choice == '3':
            self._view_budget_status()
        elif choice == '4':
            self._reset_budget()
        else:
            print("[提示] 无效选择")
    
    def _set_monthly_budget(self) -> None:
        """设置月度预算"""
        now = datetime.now()
        amount_str = self._safe_input(
            f"设置 {now.year}年{now.month}月 预算: ", 
            validator=self._validate_amount
        )
        amount = Decimal(amount_str)
        
        self._budget_manager.set_monthly_budget(now.year, now.month, amount)
        self._log(f"设置月度预算: {amount}", "info")
        if self._save_data():
            print(f"[成功] 已设置月度预算为 {amount:,.2f}")
    
    def _set_category_budget(self) -> None:
        """设置分类预算"""
        now = datetime.now()
        categories = self._default_categories["expense"]
        
        print(f"\n可选分类:")
        for i, cat in enumerate(categories, 1):
            print(f"  {i}. {cat}")
        
        cat_choice = self._safe_input(f"\n选择分类 [1-{len(categories)}]: ", default="1")
        try:
            cat_index = int(cat_choice) - 1
            category = categories[cat_index] if 0 <= cat_index < len(categories) else categories[0]
        except ValueError:
            category = categories[0]
        
        amount_str = self._safe_input(f"设置 '{category}' 预算: ", validator=self._validate_amount)
        amount = Decimal(amount_str)
        
        self._budget_manager.set_category_budget(category, now.year, now.month, amount)
        self._log(f"设置分类预算: {category}={amount}", "info")
        if self._save_data():
            print(f"[成功] 已设置 '{category}' 预算为 {amount:,.2f}")
    
    def _view_budget_status(self) -> None:
        """查看预算状态"""
        now = datetime.now()
        summary = self._budget_manager.get_budget_summary(now.year, now.month)
        
        print(f"\n--- {now.year}年{now.month}月 预算状态 ---")
        
        monthly_budget = summary['monthly_budget']
        monthly_expense = self._manager.get_monthly_statistics(now.year, now.month)['expense']
        
        if monthly_budget > 0:
            pct = float(monthly_expense / monthly_budget * 100)
            remaining = monthly_budget - monthly_expense
            bar = '█' * int(pct / 5)
            
            print(f"\n月度预算: {monthly_budget:,.2f}")
            print(f"已支出:   {monthly_expense:,.2f}  ({pct:.1f}%)")
            print(f"剩余:    {remaining:,.2f}")
            print(f"[{bar}{'░' * (20 - int(pct / 5))}]")
        else:
            print("\n尚未设置月度预算")
        
        # 分类预算
        category_budgets = summary['category_budgets']
        if category_budgets:
            print(f"\n分类预算 ({summary['category_count']} 个):")
            for b in category_budgets:
                pct = b.usage_percentage
                bar = '█' * int(pct / 5)
                status = "⚠️" if b.is_exceeded else ("!" if pct >= 80 else "")
                print(f"  {b.category:<10} {b.spent:>10,.2f}/{b.amount:>10,.2f} ({pct:>5.1f}%) {status}")
                print(f"              [{bar}{'░' * (20 - int(pct / 5))}]")
    
    def _reset_budget(self) -> None:
        """重置预算"""
        confirm = self._safe_input("确认重置所有预算? [y/N]: ", default="n")
        if confirm.lower() == 'y':
            self._budget_manager.clear()
            if self._save_data():
                print("[成功] 预算已重置")
        else:
            print("[提示] 已取消")
    
    # ==================== 导出功能 ====================
    
    def _export_menu(self) -> None:
        """导出菜单"""
        print("\n--- 数据导出 ---")
        print("1. 导出为 CSV")
        print("2. 导出为文本报表")
        
        choice = self._safe_input("\n请选择 [1-2]: ", default="1")
        
        formats = {'1': 'csv', '2': 'report'}
        format_type = formats.get(choice, 'csv')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        extension = 'csv' if format_type == 'csv' else 'txt'
        default_filename = f"finance_export_{timestamp}.{extension}"
        
        filename = self._safe_input(f"文件名 [{default_filename}]: ", default=default_filename)
        
        if self.export_data(filename, format_type):
            print(f"[成功] 数据已导出到 {filename}")
        else:
            print("[错误] 导出失败")
    
    def export_data(self, filepath: str, format_type: str = 'csv') -> bool:
        """导出数据"""
        self._state._authorize()
        transactions = self._manager.get_sorted_by_date(descending=True)
        
        if not transactions:
            print("[提示] 暂无数据可导出")
            return False
        
        return self._export_manager.export(transactions, filepath, format_type)
    
    # ==================== 辅助方法 ====================
    
    def _safe_input(
        self, 
        prompt: str, 
        default: str = None,
        validator: callable = None
    ) -> str:
        """安全的输入方法，带验证和默认值"""
        while True:
            try:
                value = input(prompt).strip()
                
                if not value and default:
                    return default
                
                if not value and not default:
                    return ""
                
                if validator:
                    validator(value)
                
                return value
                
            except ValueError as e:
                print(f"[错误] {e}")
    
    def _validate_amount(self, value: str) -> str:
        """验证金额格式"""
        try:
            amount = Decimal(value)
            if amount <= 0:
                raise ValueError("金额必须大于0")
            return value
        except:
            raise ValueError("无效的金额格式，请输入数字")
    
    def _validate_date(self, value: str) -> str:
        """验证日期格式"""
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except:
            raise ValueError("无效的日期格式，请使用 YYYY-MM-DD")
    
    def _exit_program(self) -> None:
        """退出程序"""
        self._save_data()
        self._log("程序退出", "info")
        print("\n感谢使用！再见！\n")
    
    # ==================== 命令行模式支持 ====================
    
    def _cli_add_transaction_interactive(self) -> None:
        """命令行模式添加交易"""
        self._add_transaction()
    
    def _cli_list_transactions(
        self,
        start_date: str = None,
        end_date: str = None,
        category: str = None,
        transaction_type: str = None
    ) -> None:
        """命令行模式列出交易"""
        transactions = self._manager.get_sorted_by_date(descending=True)
        
        # 过滤
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            transactions = [t for t in transactions if t.transaction_date >= start]
        
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59)
            transactions = [t for t in transactions if t.transaction_date <= end]
        
        if category:
            transactions = [t for t in transactions if t.category == category]
        
        if transaction_type:
            t_type = TransactionType.INCOME if transaction_type == 'income' else TransactionType.EXPENSE
            transactions = [t for t in transactions if t.transaction_type == t_type]
        
        print(f"共 {len(transactions)} 条记录:")
        for t in transactions:
            print(t)
    
    def _cli_show_statistics(self) -> None:
        """命令行模式显示统计"""
        self._view_statistics()
