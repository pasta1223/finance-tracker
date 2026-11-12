"""Authenticated Tkinter desktop for personal, family, and shop finances."""

import sqlite3
import tkinter as tk
import traceback
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from tkinter import ttk, messagebox

from src.models.transaction import Transaction, TransactionType
from src.services.auth_service import AuthService, AuthenticationError
from src.services.workspaces import PROFILES
from src.version import APP_VERSION


class FinanceApp(ttk.Frame):
    """One workspace; all records and charts use its authenticated state."""

    def __init__(self, root, state, on_logout=None):
        super().__init__(root)
        self.root, self.state, self.on_logout = root, state, on_logout
        self.session, self.auth = state.session, state.auth_service
        self.kind = self.session.kind if self.session else "personal"
        self.profile = PROFILES[self.kind]
        self.manager, self.budget_manager = state.transaction_manager, state.budget_manager
        self.storage = state.storage
        self.dashboard, self._poll_id, self._closed = None, None, False
        self._load_data()
        root.title(f"{self.profile['title']} · {self.session.workspace_name if self.session else '测试账本'} · v{APP_VERSION}")
        root.geometry("1320x860")
        root.minsize(1100, 760)
        self.pack(fill="both", expand=True)
        self._create_widgets()
        self.refresh_all()
        self._undo_binding = root.bind("<Control-z>", lambda _event: self.undo_action())
        self._redo_binding = root.bind("<Control-y>", lambda _event: self.redo_action())
        self._poll_id = root.after(3000, self._poll_changes)

    def _get_data_path(self):
        return self.state.storage_path

    def _load_data(self):
        loaded = self.state.load()
        if not loaded and self.state.last_error:
            raise OSError(self.state.last_error)
        if not loaded and not self.state.save():
            raise OSError(self.state.last_error)
        return loaded

    def _save_data(self):
        if self.state.save():
            return True
        error = self.state.last_error
        self.state.reload()
        self.refresh_all()
        messagebox.showerror("保存失败", f"改动未保存，已尝试重新加载最新账本。请重新操作。\n\n{error}", parent=self)
        return False

    def _create_widgets(self):
        header = tk.Frame(self, bg="#22313f", padx=22, pady=16)
        header.pack(fill="x")
        tk.Label(header, text=self.profile["title"], fg="white", bg="#22313f",
                 font=("Microsoft YaHei", 22, "bold")).pack(side="left")
        if self.session:
            tk.Label(header, text=f"{self.session.workspace_name} · {self.session.display_name} ({self.session.username})",
                     fg="#dbe4ea", bg="#22313f", padx=16).pack(side="left")
        ttk.Button(header, text="退出登录", command=self.logout).pack(side="right", padx=4)
        ttk.Button(header, text="修改密码", command=self.change_password).pack(side="right", padx=4)
        self.dashboard_btn = ttk.Button(header, text="Dashboard", command=self.open_dashboard)
        self.dashboard_btn.pack(side="right", padx=4)
        toolbar = ttk.Frame(self, padding=(18, 10))
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text=self.profile["hint"], foreground="#64748b").pack(side="left")
        ttk.Button(toolbar, text="刷新账本", command=self.reload_data).pack(side="right", padx=4)
        ttk.Button(toolbar, text="共享预算" if self.kind == "family" else "预算管理", command=self.open_budgets).pack(side="right", padx=4)
        if self.kind == "family":
            ttk.Button(toolbar, text="家庭成员", command=self.open_members).pack(side="right", padx=4)
        body = ttk.Frame(self, padding=(18, 0, 18, 12))
        body.pack(fill="both", expand=True)
        form = ttk.LabelFrame(body, text="添加收支记录", padding=16)
        form.pack(side="left", fill="y", padx=(0, 14))
        self.type_var = tk.StringVar(value="Income")
        types = ttk.Frame(form)
        types.grid(row=0, column=0, columnspan=2, pady=8)
        for label, value in (("收入", "Income"), ("支出", "Expense")):
            ttk.Radiobutton(types, text=label, value=value, variable=self.type_var, command=self._on_type_change).pack(side="left", padx=15)
        self.amount_entry = self._entry(form, 1, "金额（¥）")
        ttk.Label(form, text="分类").grid(row=2, column=0, sticky="w", pady=8)
        self.category_combo = ttk.Combobox(form, values=self._get_categories(), width=22)
        self.category_combo.grid(row=2, column=1, pady=8)
        self.category_combo.set(self._get_categories()[0])
        self.desc_entry = self._entry(form, 3, "描述")
        self.account_entry = self._entry(form, 4, "资金账户", "现金")
        self.id_entry = self._entry(form, 5, "编号（可选）")
        self.date_entry = self._entry(form, 6, "日期", datetime.now().strftime("%Y-%m-%d"))
        ttk.Label(form, text="日期格式：YYYY-MM-DD", foreground="#64748b").grid(row=7, column=0, columnspan=2)
        self.add_btn = ttk.Button(form, text="添加记录", command=self.add_transaction)
        self.add_btn.grid(row=8, column=0, columnspan=2, sticky="ew", pady=18)
        summary = ttk.LabelFrame(form, text="账本总览", padding=12)
        summary.grid(row=9, column=0, columnspan=2, sticky="ew")
        self.income_label = ttk.Label(summary, foreground="#149c68")
        self.expense_label = ttk.Label(summary, foreground="#d94848")
        self.balance_label = ttk.Label(summary)
        self.budget_label = ttk.Label(summary, wraplength=260)
        for label in (self.income_label, self.expense_label, self.balance_label, self.budget_label):
            label.pack(anchor="w", pady=5)
        self.undo_btn = ttk.Button(form, text="撤销（Ctrl+Z）", command=self.undo_action)
        self.undo_btn.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(18, 5))
        self.redo_btn = ttk.Button(form, text="重做（Ctrl+Y）", command=self.redo_action)
        self.redo_btn.grid(row=11, column=0, columnspan=2, sticky="ew")
        records = ttk.LabelFrame(body, text="家庭共享记录" if self.kind == "family" else "收支记录", padding=10)
        records.pack(side="left", fill="both", expand=True)
        filters = ttk.Frame(records)
        filters.pack(fill="x", pady=(0, 8))
        ttk.Label(filters, text="编号").pack(side="left")
        self.search_id_entry = ttk.Entry(filters, width=12)
        self.search_id_entry.pack(side="left", padx=4)
        self.search_id_entry.bind("<Return>", lambda _event: self.refresh_transaction_list())
        ttk.Button(filters, text="查询", command=self.search_by_id).pack(side="left")
        self.filter_type = ttk.Combobox(filters, values=["全部类型", "收入", "支出"], state="readonly", width=10)
        self.filter_type.set("全部类型")
        self.filter_type.pack(side="left", padx=5)
        self.filter_category = ttk.Combobox(filters, values=["全部分类"], state="readonly", width=13)
        self.filter_category.set("全部分类")
        self.filter_category.pack(side="left", padx=5)
        for combo in (self.filter_type, self.filter_category):
            combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_transaction_list())
        self.sort_desc = tk.BooleanVar(value=True)
        self.sort_btn = ttk.Button(filters, text="日期 ↓", command=self.toggle_sort)
        self.sort_btn.pack(side="right")
        self.del_btn = ttk.Button(filters, text="删除选中", command=self.delete_selected)
        self.del_btn.pack(side="right", padx=5)
        self.member_filter = None
        if self.kind == "family":
            member_bar = ttk.Frame(records)
            member_bar.pack(fill="x", pady=(0, 8))
            ttk.Label(member_bar, text="记录成员").pack(side="left", padx=(0, 8))
            self.member_filter = ttk.Combobox(member_bar, state="readonly", width=25)
            self.member_filter.set("全部成员")
            self.member_filter.pack(side="left")
            self.member_filter.bind("<<ComboboxSelected>>", lambda _event: self.refresh_transaction_list())
            ttk.Label(member_bar, text="成员可删除自己的记录，管理员可删除全部记录。", foreground="#64748b").pack(side="left", padx=10)
        table = ttk.Frame(records)
        table.pack(fill="both", expand=True)
        columns = ("ID", "Date", "Type", "Category", "Amount", "Account", "Author", "Description")
        self.tree = ttk.Treeview(table, columns=columns, show="headings", height=20)
        for key, label, width in zip(columns, ("编号", "日期", "类型", "分类", "金额", "资金账户", "记录人", "描述"), (90, 100, 50, 105, 105, 90, 140, 160)):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, minwidth=45, stretch=True)
        vertical = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(self, text="就绪", padding=(18, 8), relief="sunken")
        self.status_label.pack(fill="x", side="bottom")

    @staticmethod
    def _entry(parent, row, label, default=""):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=8, padx=(0, 10))
        entry = ttk.Entry(parent, width=24)
        entry.insert(0, default)
        entry.grid(row=row, column=1, pady=8)
        return entry

    def _get_categories(self):
        return self.profile["income_categories" if self.type_var.get() == "Income" else "expense_categories"]

    def _on_type_change(self):
        self.category_combo["values"] = self._get_categories()
        self.category_combo.set(self._get_categories()[0])

    def add_transaction(self):
        try:
            transaction = Transaction(Decimal(self.amount_entry.get().strip()),
                TransactionType.INCOME if self.type_var.get() == "Income" else TransactionType.EXPENSE,
                self.category_combo.get(), self.desc_entry.get(), self.account_entry.get() or "现金",
                datetime.strptime(self.date_entry.get().strip(), "%Y-%m-%d"), self.id_entry.get().strip() or None)
            self.manager.add(transaction)
            if self._save_data():
                for entry in (self.amount_entry, self.desc_entry, self.id_entry):
                    entry.delete(0, tk.END)
                self.refresh_all()
                self.status_label.configure(text=f"已添加 {transaction.category} ¥{transaction.amount:,.2f}")
        except Exception as error:
            self._show_error(error)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected or not messagebox.askyesno("删除记录", f"确定删除选中的 {len(selected)} 条记录？", parent=self):
            return
        try:
            if self.session and self.kind == "family" and self.session.role != "owner":
                if any(self.manager.find_by_id(key).author_id != self.session.member_id for key in selected):
                    raise AuthenticationError("只能删除自己添加的记录。")
            for key in selected:
                self.manager.remove(key)
            self._save_data()
            self.refresh_all()
        except Exception as error:
            self._show_error(error)

    def refresh_transaction_list(self):
        self.tree.delete(*self.tree.get_children())
        selected = []
        for transaction in self.manager.get_sorted_by_date(descending=self.sort_desc.get()):
            if self.search_id_entry.get().strip() and transaction.transaction_id != self.search_id_entry.get().strip():
                continue
            if self.filter_type.get() != "全部类型" and transaction.transaction_type != {"收入": TransactionType.INCOME, "支出": TransactionType.EXPENSE}.get(self.filter_type.get()):
                continue
            if self.filter_category.get() != "全部分类" and transaction.category != self.filter_category.get():
                continue
            member_id = self._member_choices.get(self.member_filter.get()) if self.member_filter else None
            if member_id and transaction.author_id != member_id:
                continue
            sign = "+" if transaction.transaction_type == TransactionType.INCOME else "-"
            self.tree.insert("", "end", iid=transaction.transaction_id, values=(transaction.transaction_id,
                transaction.transaction_date.strftime("%Y-%m-%d"), "收入" if sign == "+" else "支出",
                transaction.category, f"{sign}¥{transaction.amount:,.2f}", transaction.account,
                self._member_names.get(transaction.author_id, transaction.author_name or "历史记录"), transaction.description))
            selected.append(transaction)
        income = sum((t.amount for t in selected if t.transaction_type == TransactionType.INCOME), Decimal(0))
        expense = sum((t.amount for t in selected if t.transaction_type == TransactionType.EXPENSE), Decimal(0))
        self.status_label.configure(text=f"显示 {len(selected)}/{len(self.manager)} 条 · 筛选收入 ¥{income:,.2f} · 筛选支出 ¥{expense:,.2f}")

    def refresh_all(self):
        self.update_category_filter()
        self._member_names, self._member_choices = {}, {"全部成员": None}
        if self.member_filter:
            for member in self.auth.list_members(self.session):
                label = f"{member['display_name']} ({member['username']})"
                self._member_choices[label] = member["id"]
                self._member_names[member["id"]] = label
            self.member_filter["values"] = list(self._member_choices)
            if self.member_filter.get() not in self._member_choices:
                self.member_filter.set("全部成员")
        self.refresh_transaction_list()
        self.update_summary()
        self.update_undo_redo_buttons()

    def update_summary(self):
        self.income_label.configure(text=f"{self.profile['income']}：¥{self.manager.get_total_income():,.2f}")
        self.expense_label.configure(text=f"{self.profile['expense']}：¥{self.manager.get_total_expense():,.2f}")
        self.balance_label.configure(text=f"{self.profile['balance']}：¥{self.manager.get_balance():,.2f}")
        now = datetime.now()
        budget = self.budget_manager.get_monthly_budget(now.year, now.month)
        spent = sum((t.amount for t in self.manager.find_all() if t.transaction_type == TransactionType.EXPENSE
                     and (t.transaction_date.year, t.transaction_date.month) == (now.year, now.month)), Decimal(0))
        text = f"本月支出：¥{spent:,.2f}\n" + (f"预算余额：¥{budget - spent:,.2f}" if budget is not None else "本月尚未设置预算")
        self.budget_label.configure(text=text, foreground="#d94848" if budget is not None and spent > budget else "#64748b")
        self._refresh_dashboard()

    def update_category_filter(self):
        values = ["全部分类"] + sorted({t.category for t in self.manager.find_all()})
        self.filter_category["values"] = values
        if self.filter_category.get() not in values:
            self.filter_category.set("全部分类")

    def search_by_id(self):
        self.refresh_transaction_list()

    def toggle_sort(self):
        self.sort_desc.set(not self.sort_desc.get())
        self.sort_btn.configure(text="日期 ↓" if self.sort_desc.get() else "日期 ↑")
        self.refresh_transaction_list()

    def undo_action(self):
        self._history_action("undo")

    def redo_action(self):
        self._history_action("redo")

    def _history_action(self, action):
        try:
            if getattr(self.manager, action)():
                self._save_data()
                self.refresh_all()
        except Exception as error:
            self._show_error(error)

    def update_undo_redo_buttons(self):
        self.undo_btn.configure(state="normal" if self.manager.can_undo() else "disabled")
        self.redo_btn.configure(state="normal" if self.manager.can_redo() else "disabled")

    def reload_data(self):
        try:
            if not self.state.reload():
                raise OSError(self.state.last_error or "无法重新加载账本。")
            self.refresh_all()
        except Exception as error:
            self._show_error(error)

    def _poll_changes(self):
        if self._closed:
            return
        try:
            self.state._authorize()
            metadata = self.storage.get_metadata()
            if metadata.get("error"):
                raise OSError(metadata["error"])
            if metadata.get("revision", 0) != self.state._storage_revision:
                self.reload_data()
        except AuthenticationError as error:
            messagebox.showerror("请重新登录", str(error), parent=self)
            self.logout()
        except (OSError, sqlite3.Error) as error:
            self.status_label.configure(text=f"刷新暂时失败：{error}")
        finally:
            if not self._closed:
                self._poll_id = self.root.after(3000, self._poll_changes)

    def open_dashboard(self):
        try:
            self.state._authorize()
            if self.dashboard and self.dashboard.is_open():
                self.dashboard.refresh()
                self.dashboard.focus()
                return
            from src.ui.dashboard import FinanceDashboard
            self.dashboard = FinanceDashboard(self.root, self._dashboard_transactions, kind=self.kind,
                workspace_name=self.session.workspace_name if self.session else "")
        except Exception as error:
            log_path = Path(self._get_data_path()).parent / "dashboard_error.log"
            try:
                with log_path.open("a", encoding="utf-8") as stream:
                    stream.write(f"\n[{datetime.now().isoformat()}]\n{traceback.format_exc()}")
            except OSError:
                pass
            self._show_error(error)

    def _dashboard_transactions(self):
        self.state._authorize()
        return self.manager.find_all()

    def _refresh_dashboard(self):
        if self.dashboard and self.dashboard.is_open():
            self.dashboard.refresh()

    def _dialog(self, title):
        window = tk.Toplevel(self.root)
        window.title(title)
        window.transient(self.root)
        content = ttk.Frame(window, padding=20)
        content.pack(fill="both", expand=True)
        return window, content

    def open_budgets(self):
        from src.ui.budget_panel import BudgetPanel
        window, content = self._dialog("家庭共享预算" if self.kind == "family" else "预算管理")
        BudgetPanel(content, self.state, self._save_data, self.refresh_all).pack(fill="both", expand=True)

    def open_members(self):
        try:
            members = self.auth.list_members(self.session)
            window, content = self._dialog(f"家庭成员 · {self.session.workspace_name}")
            ttk.Label(content, text=f"家庭账号：{self.session.account}", font=("Microsoft YaHei", 13, "bold")).pack(anchor="w", pady=(0, 12))
            for member in members:
                role = "管理员" if member["role"] == "owner" else "成员"
                ttk.Label(content, text=f"{member['display_name']}（{member['username']}） · {role}").pack(anchor="w", pady=5)
            if self.session.role == "owner":
                code = tk.StringVar()
                ttk.Label(content, text="生成后将家庭账号和邀请码告知成员；重新生成会使旧邀请码失效。", wraplength=460).pack(pady=(18, 8))
                ttk.Entry(content, textvariable=code, state="readonly", width=40).pack(fill="x", pady=5)
                def generate():
                    try:
                        code.set(self.auth.rotate_invite(self.session))
                    except Exception as error:
                        self._show_error(error)
                ttk.Button(content, text="生成 / 更新邀请码", command=generate).pack(pady=8)
        except Exception as error:
            self._show_error(error)

    def change_password(self):
        window, content = self._dialog("修改当前登录账号的密码")
        entries = [self._entry(content, row, label) for row, label in enumerate(("原密码", "新密码", "确认新密码"))]
        for entry in entries:
            entry.configure(show="●")
        def save():
            if entries[1].get() != entries[2].get():
                messagebox.showwarning("请检查密码", "两次输入的新密码不一致。", parent=window)
                return
            try:
                self.auth.change_password(self.session, entries[0].get(), entries[1].get())
                messagebox.showinfo("密码已更新", "请使用新密码重新登录。", parent=window)
                self.logout()
            except Exception as error:
                self._show_error(error)
        ttk.Button(content, text="保存新密码", command=save).grid(row=3, column=0, columnspan=2, pady=14)

    def _show_error(self, error):
        messagebox.showerror("操作失败", str(error) or "请输入正确的金额和日期。", parent=self)

    def logout(self):
        if self.on_logout:
            self.on_logout()

    def close(self):
        self._closed = True
        if self._poll_id:
            self.root.after_cancel(self._poll_id)
        self.root.unbind("<Control-z>", self._undo_binding)
        self.root.unbind("<Control-y>", self._redo_binding)
        if self.dashboard:
            self.dashboard.close()
        for window in self.root.winfo_children():
            if isinstance(window, tk.Toplevel):
                window.destroy()
        self.manager.from_dict({})
        self.budget_manager.clear()
        self.state._authors.clear()
        self.state._baseline.clear()
        self.destroy()


class FinanceDesktop:
    def __init__(self, root, auth=None):
        self.root, self.auth = root, auth or AuthService()
        self.view = self.app = self.session = None
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.show_login()

    def show_login(self):
        from src.ui.login import LoginView
        self.view = LoginView(self.root, self.auth, self.login)

    def login(self, session):
        state = self.auth.open_state(session)
        previous = set(self.root.winfo_children())
        try:
            app = FinanceApp(self.root, state, self.logout)
        except Exception:
            for widget in set(self.root.winfo_children()) - previous:
                widget.destroy()
            self.auth.logout(session)
            raise
        self.view.destroy()
        self.view = None
        self.app, self.session = app, session

    def logout(self):
        if self.session:
            self.auth.logout(self.session)
        if self.app:
            self.app.close()
        self.app = self.session = None
        self.show_login()

    def close(self):
        if self.session:
            self.auth.logout(self.session)
        if self.app:
            self.app.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    ttk.Style(root).configure("TLabel", font=("Microsoft YaHei", 10))
    desktop = FinanceDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()
