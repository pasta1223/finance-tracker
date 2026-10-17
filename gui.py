"""
个人财务管理系统 - Tkinter 图形界面版
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from decimal import Decimal
import os
import sys
import traceback

sys.path.append(os.path.dirname(__file__))

from src.models.transaction import Transaction, TransactionType
from src.services.application_state import FinanceApplicationState
from src.version import APP_VERSION


class FinanceApp:
    """财务管理系统主窗口"""
    
    def __init__(self, root, state=None):
        self.root = root
        self.root.title(f"Personal Finance Tracker v{APP_VERSION}")
        self.root.geometry("1100x800")
        self.root.resizable(True, True)
        
        # GUI and CLI share the same application state and SQLite database.
        self.state = state or FinanceApplicationState()
        self.manager = self.state.transaction_manager
        self.budget_manager = self.state.budget_manager
        self.storage = self.state.storage
        self.dashboard = None
        self._load_data()
        
        # 设置颜色和字体
        self.colors = {
            "bg": "#f0f0f0",
            "income": "#00cc66",
            "expense": "#ff4444",
            "button": "#4a90d9"
        }
        
        # 创建界面
        self._create_widgets()
        
        # 刷新显示
        self.refresh_transaction_list()
        self.update_summary()
        self.update_undo_redo_buttons()

    def _get_data_path(self):
        """Return the shared SQLite database path used by every UI."""
        return self.state.storage_path
    
    def _load_data(self):
        """Load transactions and budgets through the shared application state."""
        return self.state.load()
    
    def _save_data(self):
        """Save transactions and budgets together through shared SQLite state."""
        if self.state.save():
            return True

        error = self.state.last_error or "Unknown SQLite storage error"
        self.state.reload()
        messagebox.showerror(
            "Save failed",
            f"The transaction was not saved. The latest database state was reloaded.\n\n{error}",
        )
        return False
    
    def _create_widgets(self):
        """创建所有界面组件"""
        
        # 顶部标题
        title_frame = tk.Frame(self.root, bg="#2c3e50", height=80)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame, 
            text="💰 Personal Finance Tracker",
            font=("微软雅黑", 24, "bold"),
            fg="white", 
            bg="#2c3e50"
        )
        title_label.pack(expand=True)

        self.dashboard_btn = tk.Button(
            title_frame,
            text="📊 Dashboard",
            bg="#3478c0",
            fg="white",
            activebackground="#2c68a8",
            activeforeground="white",
            relief="flat",
            padx=14,
            pady=7,
            font=("微软雅黑", 10, "bold"),
            command=self.open_dashboard,
        )
        self.dashboard_btn.place(relx=0.98, rely=0.5, anchor="e")
        
        # 主内容区域（左右分栏）
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ========== 左侧：添加记录表单 ==========
        left_frame = tk.LabelFrame(main_frame, text="Add Transaction", font=("微软雅黑", 12, "bold"), padx=10, pady=10)
        left_frame.pack(side="left", fill="y", padx=(0, 10))
        
        # 交易类型
        tk.Label(left_frame, text="Type:", font=("微软雅黑", 10)).grid(row=0, column=0, sticky="w", pady=5)
        self.type_var = tk.StringVar(value="Income")
        type_frame = tk.Frame(left_frame)
        type_frame.grid(row=0, column=1, sticky="w", pady=5)
        tk.Radiobutton(type_frame, text="Income", variable=self.type_var, value="Income", command=self._on_type_change).pack(side="left")
        tk.Radiobutton(type_frame, text="Expense", variable=self.type_var, value="Expense", command=self._on_type_change).pack(side="left")
        
        # 金额
        tk.Label(left_frame, text="Amount (¥):", font=("微软雅黑", 10)).grid(row=1, column=0, sticky="w", pady=5)
        self.amount_entry = tk.Entry(left_frame, font=("微软雅黑", 10), width=20)
        self.amount_entry.grid(row=1, column=1, pady=5)
        
        # 分类
        tk.Label(left_frame, text="Category:", font=("微软雅黑", 10)).grid(row=2, column=0, sticky="w", pady=5)
        self.category_combo = ttk.Combobox(left_frame, values=self._get_categories(), width=18)
        self.category_combo.grid(row=2, column=1, pady=5)
        self.category_combo.set("Salary")
        
        # 描述
        tk.Label(left_frame, text="Description:", font=("微软雅黑", 10)).grid(row=3, column=0, sticky="w", pady=5)
        self.desc_entry = tk.Entry(left_frame, font=("微软雅黑", 10), width=20)
        self.desc_entry.grid(row=3, column=1, pady=5)
        
        # 账户
        tk.Label(left_frame, text="Account:", font=("微软雅黑", 10)).grid(row=4, column=0, sticky="w", pady=5)
        self.account_entry = tk.Entry(left_frame, font=("微软雅黑", 10), width=20)
        self.account_entry.insert(0, "Default account")
        self.account_entry.grid(row=4, column=1, pady=5)

        #ID
        tk.Label(left_frame, text="id(Optional):", font=("微软雅黑", 10)).grid(row=5, column=0, sticky="w", pady=5)
        self.id_entry = tk.Entry(left_frame, font=("微软雅黑", 10), width=20)
        self.id_entry.grid(row=5, column=1, pady=5)

        #日期
        tk.Label(left_frame, text="Date:", font=("微软雅黑", 10)).grid(row=6, column=0, sticky="w", pady=5)
        self.date_entry = tk.Entry(left_frame, font=("微软雅黑", 10), width=20)
        self.date_entry.insert(0, f"{datetime.now().date()}")
        self.date_entry.grid(row=6, column=1, pady=5)

        # 添加按钮
        self.add_btn = tk.Button(
            left_frame, 
            text="➕ Add record",
            bg=self.colors["button"], 
            fg="white",
            font=("微软雅黑", 10, "bold"),
            command=self.add_transaction
        )
        self.add_btn.grid(row=7, column=0, columnspan=2, pady=20, sticky="ew")
        
        # 统计摘要
        summary_frame = tk.LabelFrame(left_frame, text="Summary", font=("微软雅黑", 10, "bold"), padx=10, pady=10)
        summary_frame.grid(row=8, column=0, columnspan=2, sticky="ew", pady=10)
        
        self.income_label = tk.Label(summary_frame, text="Total income: ¥0", fg=self.colors["income"], font=("微软雅黑", 10))
        self.income_label.pack(anchor="w", pady=2)
        
        self.expense_label = tk.Label(summary_frame, text="Total expense: ¥0", fg=self.colors["expense"], font=("微软雅黑", 10))
        self.expense_label.pack(anchor="w", pady=2)
        
        self.balance_label = tk.Label(summary_frame, text="Balance: ¥0", font=("微软雅黑", 10, "bold"))
        self.balance_label.pack(anchor="w", pady=2)
        
        # 撤销/重做按钮区域
        undo_frame = tk.LabelFrame(left_frame, text="Undo/Redo", font=("微软雅黑", 10, "bold"), padx=10, pady=10)
        undo_frame.grid(row=9, column=0, columnspan=2, sticky="ew", pady=10)
        
        self.undo_btn = tk.Button(
            undo_frame, 
            text="↩️ Undo (Ctrl+Z)",
            bg="#f0ad4e", 
            fg="white",
            font=("微软雅黑", 9),
            command=self.undo_action,
            state="disabled"
        )
        self.undo_btn.pack(fill="x", pady=2)
        
        self.redo_btn = tk.Button(
            undo_frame, 
            text="↪️ Redo (Ctrl+Y)",
            bg="#5bc0de", 
            fg="white",
            font=("微软雅黑", 9),
            command=self.redo_action,
            state="disabled"
        )
        self.redo_btn.pack(fill="x", pady=2)
        
        # ========== 右侧：记录列表 ==========
        right_frame = tk.LabelFrame(main_frame, text="Transactions", font=("微软雅黑", 12, "bold"), padx=10, pady=10)
        right_frame.pack(side="right", fill="both", expand=True)
        
        # 筛选栏
        filter_frame = tk.Frame(right_frame)
        filter_frame.pack(fill="x", pady=5)
        
        tk.Label(filter_frame, text="Search ID:", font=("微软雅黑", 9)).pack(side="left", padx=(5, 0))
        self.search_id_entry = tk.Entry(filter_frame, font=("微软雅黑", 9), width=15)
        self.search_id_entry.pack(side="left", padx=5)
        tk.Button(filter_frame, text="🔍 Search", font=("微软雅黑", 8), command=self.search_by_id).pack(side="left", padx=2)
        
        tk.Label(filter_frame, text="|", font=("微软雅黑", 9), fg="#999").pack(side="left", padx=5)
        
        tk.Label(filter_frame, text="Filter:", font=("微软雅黑", 9)).pack(side="left", padx=5)
        
        self.filter_type = ttk.Combobox(filter_frame, values=["All", "Income", "Expense"], width=8)
        self.filter_type.set("All")
        self.filter_type.pack(side="left", padx=5)
        self.filter_type.bind("<<ComboboxSelected>>", lambda e: self.refresh_transaction_list())
        
        tk.Label(filter_frame, text="Category:", font=("微软雅黑", 9)).pack(side="left", padx=5)
        
        self.filter_category = ttk.Combobox(filter_frame, values=["All"], width=10)
        self.filter_category.set("All")
        self.filter_category.pack(side="left", padx=5)
        self.filter_category.bind("<<ComboboxSelected>>", lambda e: self.refresh_transaction_list())
        
        # 排序按钮
        self.sort_desc = tk.BooleanVar(value=True)  # 默认降序（最新在前）
        self.sort_btn = tk.Button(
            filter_frame, 
            text="📅 Date↓",
            font=("微软雅黑", 8),
            command=self.toggle_sort
        )
        self.sort_btn.pack(side="left", padx=5)
        
        # 删除按钮
        self.del_btn = tk.Button(
            filter_frame, 
            text="🗑️ Delete",
            bg="#ff6666", 
            fg="white",
            command=self.delete_selected
        )
        self.del_btn.pack(side="right", padx=5)
        
        # 交易列表（Treeview表格）
        columns = ("ID", "Date", "Type", "Category", "Amount", "Description")
        self.tree = ttk.Treeview(right_frame, columns=columns, show="headings", height=20)
        
        self.tree.heading("ID", text="ID")
        self.tree.heading("Date", text="Date")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Category", text="Category")
        self.tree.heading("Amount", text="Amount")
        self.tree.heading("Description", text="Description")
        
        self.tree.column("ID", width=80)
        self.tree.column("Date", width=100)
        self.tree.column("Type", width=60)
        self.tree.column("Category", width=100)
        self.tree.column("Amount", width=100)
        self.tree.column("Description", width=150)
        
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 底部状态栏
        status_frame = tk.Frame(self.root, relief="sunken", bd=1)
        status_frame.pack(side="bottom", fill="x")
        
        self.status_label = tk.Label(status_frame, text="Ready", anchor="w", padx=5)
        self.status_label.pack(fill="x")
    
    def _get_categories(self):
        """获取分类列表"""
        if self.type_var.get() == "Income":
            return ["Salary", "Bonus", "Investment", "Part-time job", "Other income"]
        else:
            return ["Catering", "Traffic", "Shopping", "Living", "Medical", "Education", "Fun", "Chatting", "Other expense"]
    
    def _on_type_change(self):
        """交易类型改变时更新分类下拉框"""
        self.category_combo["values"] = self._get_categories()
        self.category_combo.set(self._get_categories()[0])
        self.refresh_transaction_list()
    
    def add_transaction(self):
        """添加交易记录"""
        try:
            amount_str = self.amount_entry.get().strip()
            if not amount_str:
                messagebox.showwarning("Warning", "Please enter amount.")
                return
            
            amount = Decimal(amount_str)
            if amount <= 0:
                messagebox.showwarning("Warning", "Amount must be greater than 0.")
                return
            
            trans_type = TransactionType.INCOME if self.type_var.get() == "Income" else TransactionType.EXPENSE
            category = self.category_combo.get()
            description = self.desc_entry.get()
            account = self.account_entry.get() or "Default account"
            ID=self.id_entry.get()
            date=datetime.strptime(self.date_entry.get(),"%Y-%m-%d")
            
            transaction = Transaction(
                amount=amount,
                transaction_type=trans_type,
                category=category,
                description=description,
                account=account,
                transaction_id=ID,
                transaction_date=date
            )
            
            self.manager.add(transaction)
            if not self._save_data():
                return
            
            # 清空表单
            self.amount_entry.delete(0, tk.END)
            self.desc_entry.delete(0, tk.END)
            
            # 刷新界面
            self.refresh_transaction_list()
            self.update_summary()
            self.update_category_filter()
            self.update_undo_redo_buttons()
            
            self.status_label.config(text=f"Record added: {category} ¥{amount:,.2f}")
            messagebox.showinfo("Success", f"Added {self.type_var.get()} records！")
            
        except Exception as e:
            messagebox.showerror("Error", f"Addition failed: {e}")
    
    def delete_selected(self):
        """删除选中的记录"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a transaction.")
            return
        
        deleted_count = 0
        if messagebox.askyesno("Confirm deletion", "Sure you want to delete the transaction?"):
            for item in selected:
                trans_id = str(self.tree.item(item)["values"][0])
                try:
                    self.manager.remove(trans_id)
                    deleted_count += 1
                except Exception as e:
                    print(f"Deletion failed: {e}.")
            
            if deleted_count > 0:
                if not self._save_data():
                    self.refresh_transaction_list()
                    self.update_summary()
                    self.update_category_filter()
                    self.update_undo_redo_buttons()
                    return
                self.refresh_transaction_list()
                self.update_summary()
                self.update_category_filter()
                self.update_undo_redo_buttons()
                self.status_label.config(text=f"Deleted {deleted_count} records.")
            else:
                messagebox.showerror("Error", "Deletion failed.")
    
    def refresh_transaction_list(self):
        """刷新交易列表"""
        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 获取所有记录（根据排序设置）
        transactions = self.manager.get_sorted_by_date(descending=self.sort_desc.get())
        
        # 应用筛选
        filter_t = self.filter_type.get()
        filter_cat = self.filter_category.get()
        
        display_count = 0
        for t in transactions:
            # 类型筛选
            if filter_t == "Income" and t.transaction_type != TransactionType.INCOME:
                continue
            if filter_t == "Expense" and t.transaction_type != TransactionType.EXPENSE:
                continue
            
            # 分类筛选
            if filter_cat != "All" and t.category != filter_cat:
                continue
            
            sign = "+" if t.transaction_type == TransactionType.INCOME else "-"
            self.tree.insert("", "end", values=(
                t.transaction_id,
                t.transaction_date.strftime("%Y-%m-%d"),
                t.transaction_type.value,
                t.category,
                f"{sign}¥{t.amount:,.2f}",
                t.description or ""
            ))
            display_count += 1
        
        total = len(transactions)
        if display_count == total:
            self.status_label.config(text=f"Total : {total} records")
        else:
            self.status_label.config(text=f"Show {display_count}/{total} records")
    
    def update_summary(self):
        """更新摘要统计"""
        income = self.manager.get_total_income()
        expense = self.manager.get_total_expense()
        balance = self.manager.get_balance()
        
        self.income_label.config(text=f"Total income: ¥{income:,.2f}")
        self.expense_label.config(text=f"Total expense: ¥{expense:,.2f}")
        self.balance_label.config(text=f"Balance: ¥{balance:,.2f}")
        self._refresh_dashboard()

    def open_dashboard(self):
        """打开数据可视化看板；重复点击时复用已有窗口。"""
        try:
            if self.dashboard is not None and self.dashboard.is_open():
                self.dashboard.refresh()
                self.dashboard.focus()
                return

            # 延迟导入，让未安装图表依赖时主界面仍能正常启动。
            from src.ui.dashboard import FinanceDashboard

            self.dashboard = FinanceDashboard(self.root, self.manager.find_all)
        except ModuleNotFoundError as error:
            log_path = self._log_dashboard_error()
            messagebox.showerror(
                "Dashboard unavailable",
                f"A chart dependency is missing: {error}\n\n"
                f"Error details were saved to:\n{log_path}",
            )
        except Exception as error:
            log_path = self._log_dashboard_error()
            messagebox.showerror(
                "Dashboard error",
                f"Unable to open dashboard: {error}\n\n"
                f"Error details were saved to:\n{log_path}",
            )

    def _log_dashboard_error(self):
        """Persist the full dashboard traceback next to the application data."""
        log_path = os.path.join(
            os.path.dirname(self._get_data_path()), "dashboard_error.log"
        )
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"\n[{datetime.now().isoformat()}]\n")
                log_file.write(traceback.format_exc())
        except OSError:
            pass
        return log_path

    def _refresh_dashboard(self):
        """Refresh the open dashboard after transaction data changes."""
        if self.dashboard is not None and self.dashboard.is_open():
            self.dashboard.refresh()
    
    def update_category_filter(self):
        """更新分类筛选下拉框"""
        categories = set()
        for t in self.manager.find_all():
            categories.add(t.category)
        
        self.filter_category["values"] = ["All"] + sorted(list(categories))
    
    def search_by_id(self):
        """按ID搜索记录"""
        search_id = self.search_id_entry.get().strip()
        if not search_id:
            self.refresh_transaction_list()
            return
        
        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 查找记录
        transaction = self.manager.find_by_id(search_id)
        
        if transaction:
            sign = "+" if transaction.transaction_type == TransactionType.INCOME else "-"
            self.tree.insert("", "end", values=(
                transaction.transaction_id,
                transaction.transaction_date.strftime("%Y-%m-%d"),
                transaction.transaction_type.value,
                transaction.category,
                f"{sign}¥{transaction.amount:,.2f}",
                transaction.description or ""
            ))
            self.status_label.config(text=f"Found record: ID={search_id}")
        else:
            self.status_label.config(text=f"Unfound records: ID={search_id}")
    
    def toggle_sort(self):
        """切换日期排序顺序"""
        self.sort_desc.set(not self.sort_desc.get())
        if self.sort_desc.get():
            self.sort_btn.config(text="📅 Date↓")
        else:
            self.sort_btn.config(text="📅 Date↑")
        self.refresh_transaction_list()

    def undo_action(self):
        """撤销上一个操作"""
        if not self.manager.can_undo():
            messagebox.showinfo("Warning", "No undo operation")
            return
        
        action = self.manager.get_last_action()
        action_desc = action.get("action", "Operation") if action else "Unknown"
        
        if messagebox.askyesno("Confirm undo", f"Sure to undo「{action_desc}」Operation？"):
            if self.manager.undo():
                if not self._save_data():
                    self.refresh_transaction_list()
                    self.update_summary()
                    self.update_category_filter()
                    self.update_undo_redo_buttons()
                    return
                self.refresh_transaction_list()
                self.update_summary()
                self.update_category_filter()
                self.update_undo_redo_buttons()
                self.status_label.config(text=f"Undid: {action_desc}")
    
    def redo_action(self):
        """重做上一个撤销的操作"""
        if not self.manager.can_redo():
            messagebox.showinfo("Warning", "No redo operation")
            return
        
        action = self.manager.get_last_redo_action()
        action_desc = action.get("action", "Operation") if action else "Unknown"
        
        if self.manager.redo():
            if not self._save_data():
                self.refresh_transaction_list()
                self.update_summary()
                self.update_category_filter()
                self.update_undo_redo_buttons()
                return
            self.refresh_transaction_list()
            self.update_summary()
            self.update_category_filter()
            self.update_undo_redo_buttons()
            self.status_label.config(text=f"Redid: {action_desc}")
    
    def update_undo_redo_buttons(self):
        """更新撤销/重做按钮状态"""
        self.undo_btn.config(state="normal" if self.manager.can_undo() else "disabled")
        self.redo_btn.config(state="normal" if self.manager.can_redo() else "disabled")


def main():
    root = tk.Tk()
    app = FinanceApp(root)
    
    # 绑定快捷键
    app.root.bind('<Control-z>', lambda e: app.undo_action())
    app.root.bind('<Control-y>', lambda e: app.redo_action())

    # Non-interactive packaged-build check. It is inactive during normal use.
    smoke_result = os.environ.get("FINANCE_TRACKER_SMOKE_RESULT")
    if smoke_result:
        def verify_packaged_dashboard():
            app.open_dashboard()
            succeeded = app.dashboard is not None and app.dashboard.is_open()
            with open(smoke_result, "w", encoding="utf-8") as result_file:
                result_file.write("ok" if succeeded else "error")
            root.after(500, root.destroy)

        root.after(500, verify_packaged_dashboard)
    
    root.mainloop()


if __name__ == "__main__":
    main()
