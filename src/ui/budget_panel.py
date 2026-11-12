"""Monthly and category budgets with spending computed from the live ledger."""

import tkinter as tk
from datetime import datetime
from decimal import Decimal
from tkinter import ttk, messagebox

from ..models.transaction import TransactionType


class BudgetPanel(ttk.Frame):
    def __init__(self, parent, state, save_callback, refresh_callback):
        super().__init__(parent)
        self.state, self.save_callback, self.refresh_callback = state, save_callback, refresh_callback
        form = ttk.Frame(self)
        form.pack(fill="x")
        self.month = tk.StringVar(value=datetime.now().strftime("%Y-%m"))
        self.category = tk.StringVar(value="月度总预算")
        self.amount = tk.StringVar()
        fields = (("月份（YYYY-MM）", self.month), ("分类（或选择总预算）", self.category), ("预算金额（¥）", self.amount))
        for row, (label, variable) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=(0, 15), pady=7)
            if row == 1:
                categories = sorted({t.category for t in state.transaction_manager.find_all()})
                widget = ttk.Combobox(form, textvariable=variable, values=["月度总预算"] + categories, width=26)
            else:
                widget = ttk.Entry(form, textvariable=variable, width=28)
            widget.grid(row=row, column=1, pady=7)
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=10)
        ttk.Button(buttons, text="查看月份", command=self.refresh).pack(side="left")
        ttk.Button(buttons, text="保存预算", command=self.save).pack(side="right")
        self.summary = ttk.Label(self, wraplength=560)
        self.summary.pack(anchor="w", pady=8)
        self.tree = ttk.Treeview(self, columns=("category", "amount", "spent", "remaining"), show="headings", height=8)
        for key, label in (("category", "分类"), ("amount", "预算"), ("spent", "已支出"), ("remaining", "余额")):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=130)
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("exceeded", foreground="#d94848")
        self.refresh()

    def _period(self):
        value = datetime.strptime(self.month.get().strip(), "%Y-%m")
        return value.year, value.month

    def refresh(self):
        try:
            self.state._authorize()
            year, month = self._period()
            expenses = [t for t in self.state.transaction_manager.find_all()
                        if t.transaction_type == TransactionType.EXPENSE
                        and (t.transaction_date.year, t.transaction_date.month) == (year, month)]
            spent = sum((t.amount for t in expenses), Decimal(0))
            manager = self.state.budget_manager
            budget = manager.get_monthly_budget(year, month)
            self.summary.configure(text=f"本月总支出 ¥{spent:,.2f} · " +
                (f"总预算 ¥{budget:,.2f} · 剩余 ¥{budget - spent:,.2f}" if budget is not None else "尚未设置月度总预算"))
            self.tree.delete(*self.tree.get_children())
            for item in manager.get_all_category_budgets(year, month):
                category_spent = sum((t.amount for t in expenses if t.category == item.category), Decimal(0))
                self.tree.insert("", "end", values=(item.category, f"¥{item.amount:,.2f}", f"¥{category_spent:,.2f}",
                    f"¥{item.amount - category_spent:,.2f}"), tags=("exceeded",) if category_spent > item.amount else ())
        except Exception as error:
            messagebox.showerror("无法查看预算", str(error), parent=self)

    def save(self):
        try:
            self.state._authorize()
            year, month = self._period()
            amount = Decimal(self.amount.get().strip())
            if not amount.is_finite() or amount < 0:
                raise ValueError("预算金额必须为大于或等于 0 的有效数值。")
            amount = amount.quantize(Decimal("0.01"))
            category = self.category.get().strip()
            if not category:
                raise ValueError("请输入分类或选择月度总预算。")
            if category == "月度总预算":
                self.state.budget_manager.set_monthly_budget(year, month, amount)
            else:
                self.state.budget_manager.set_category_budget(category, year, month, amount)
            if self.save_callback():
                self.refresh_callback()
            self.refresh()
        except Exception as error:
            messagebox.showerror("预算保存失败", str(error), parent=self)
