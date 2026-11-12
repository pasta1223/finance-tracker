"""Matplotlib dashboard embedded in a Tkinter top-level window."""

import tkinter as tk
from datetime import timedelta
from tkinter import ttk
from typing import Callable, Iterable

from matplotlib import rcParams
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from matplotlib.dates import DateFormatter

from ..models.transaction import Transaction
from ..services.analytics import DashboardData, build_dashboard_data
from ..services.workspaces import PROFILES


class FinanceDashboard:
    """Interactive financial dashboard backed by the live transaction manager."""

    PERIODS = {
        "最近 6 个月": 6,
        "最近 12 个月": 12,
        "全部时间": None,
    }

    def __init__(
        self,
        parent: tk.Misc,
        transaction_provider: Callable[[], Iterable[Transaction]],
        *, kind: str = "personal", workspace_name: str = "",
    ) -> None:
        self._transaction_provider = transaction_provider
        self.kind = kind
        self.profile = PROFILES[kind]
        self.title = self.profile["title"] + " Dashboard" + (f" · {workspace_name}" if workspace_name else "")
        self.window = tk.Toplevel(parent)
        self.window.title(self.title)
        self.window.geometry("1120x760")
        self.window.minsize(900, 620)
        self.window.configure(bg="#f4f6f8")

        rcParams["font.sans-serif"] = [
            "Microsoft YaHei",
            "SimHei",
            "Arial Unicode MS",
            "DejaVu Sans",
        ]
        rcParams["axes.unicode_minus"] = False

        self._build_header()
        self._build_kpis()
        self._build_chart_area()
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()

    def _build_header(self) -> None:
        header = tk.Frame(self.window, bg="#22313f", height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text=self.title,
            bg="#22313f",
            fg="white",
            font=("Microsoft YaHei", 20, "bold"),
        ).pack(side="left", padx=22)

        controls = tk.Frame(header, bg="#22313f")
        controls.pack(side="right", padx=18, pady=14)
        tk.Label(
            controls,
            text="期间：",
            bg="#22313f",
            fg="#dbe4ea",
            font=("Microsoft YaHei", 10),
        ).pack(side="left", padx=(0, 6))

        self.period_var = tk.StringVar(value="最近 6 个月")
        period_box = ttk.Combobox(
            controls,
            textvariable=self.period_var,
            values=list(self.PERIODS),
            state="readonly",
            width=17,
        )
        period_box.pack(side="left", padx=(0, 8))
        period_box.bind("<<ComboboxSelected>>", lambda _event: self.refresh())

        ttk.Button(controls, text="刷新", command=self.refresh).pack(side="left")

    def _build_kpis(self) -> None:
        container = tk.Frame(self.window, bg="#f4f6f8")
        container.pack(fill="x", padx=16, pady=(14, 4))
        self._kpi_values = {}

        cards = (
            (self.profile["income"], "income", "#149c68"),
            (self.profile["expense"], "expense", "#e05252"),
            (self.profile["balance"], "balance", "#3478c0"),
            ("交易记录", "count", "#7656a8"),
        )
        for title, key, color in cards:
            card = tk.Frame(
                container,
                bg="white",
                highlightbackground="#dfe5e8",
                highlightthickness=1,
                padx=14,
                pady=10,
            )
            card.pack(side="left", fill="x", expand=True, padx=5)
            tk.Label(
                card,
                text=title,
                bg="white",
                fg="#66737c",
                font=("Microsoft YaHei", 9),
            ).pack(anchor="w")
            value_label = tk.Label(
                card,
                text="--",
                bg="white",
                fg=color,
                font=("Microsoft YaHei", 16, "bold"),
            )
            value_label.pack(anchor="w", pady=(3, 0))
            self._kpi_values[key] = value_label

    def _build_chart_area(self) -> None:
        chart_frame = tk.Frame(self.window, bg="#f4f6f8")
        chart_frame.pack(fill="both", expand=True, padx=18, pady=(4, 14))

        self.figure = Figure(figsize=(11, 6.2), dpi=100, facecolor="white")
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        toolbar_frame = tk.Frame(chart_frame, bg="white")
        toolbar_frame.pack(fill="x")
        self.toolbar = NavigationToolbar2Tk(
            self.canvas, toolbar_frame, pack_toolbar=False
        )
        self.toolbar.update()
        self.toolbar.pack(side="left")

    @staticmethod
    def _money_axis(value: float, _position: int) -> str:
        absolute = abs(value)
        if absolute >= 1_000_000:
            return f"¥{value / 1_000_000:.1f}M"
        if absolute >= 1_000:
            return f"¥{value / 1_000:.1f}K"
        return f"¥{value:,.0f}"

    def _update_kpis(self, data: DashboardData) -> None:
        self._kpi_values["income"].config(text=f"¥{data.total_income:,.2f}")
        self._kpi_values["expense"].config(text=f"¥{data.total_expense:,.2f}")
        self._kpi_values["balance"].config(text=f"¥{data.balance:,.2f}")
        self._kpi_values["balance"].config(
            fg="#149c68" if data.balance >= 0 else "#e05252"
        )
        self._kpi_values["count"].config(text=str(data.transaction_count))

    def refresh(self) -> None:
        """Re-query the manager and redraw every dashboard component."""

        if not self.is_open():
            return
        period = self.PERIODS[self.period_var.get()]
        data = build_dashboard_data(self._transaction_provider(), period)
        self._update_kpis(data)
        self._draw_charts(data)

    def _draw_charts(self, data: DashboardData) -> None:
        self.figure.clear()
        if not data.transactions:
            empty = self.figure.add_subplot(111)
            empty.axis("off")
            empty.text(
                0.5,
                0.54,
                "所选期间没有收支记录",
                ha="center",
                va="center",
                fontsize=17,
                color="#66737c",
                transform=empty.transAxes,
            )
            empty.text(
                0.5,
                0.46,
                "添加记录或切换查看期间。",
                ha="center",
                va="center",
                fontsize=10,
                color="#9aa4ab",
                transform=empty.transAxes,
            )
            self.canvas.draw_idle()
            return

        grid = self.figure.add_gridspec(
            2, 2, height_ratios=(1, 1), width_ratios=(1.55, 1), hspace=0.42, wspace=0.28
        )
        monthly_axis = self.figure.add_subplot(grid[0, 0])
        category_axis = self.figure.add_subplot(grid[0, 1])
        trend_axis = self.figure.add_subplot(grid[1, 0] if self.kind == "family" else grid[1, :])

        self._draw_monthly(monthly_axis, data)
        self._draw_categories(category_axis, data)
        self._draw_trend(trend_axis, data)
        if self.kind == "family":
            self._draw_members(self.figure.add_subplot(grid[1, 1]), data)
        self.figure.subplots_adjust(left=0.07, right=0.96, top=0.94, bottom=0.12)
        self.canvas.draw_idle()

    def _draw_members(self, axis, data):
        from ..services.analytics import build_member_totals
        totals = build_member_totals(data.transactions)
        positions = list(range(len(totals)))
        axis.bar([i - 0.18 for i in positions], [float(t[2]) for t in totals], 0.36, label="成员收入", color="#26b37b")
        axis.bar([i + 0.18 for i in positions], [float(t[3]) for t in totals], 0.36, label="成员支出", color="#f06b6b")
        axis.set_xticks(positions)
        axis.set_xticklabels([t[1] for t in totals])
        axis.set_title("家庭成员收支（所选期间）", loc="left", fontsize=11, fontweight="bold")
        axis.yaxis.set_major_formatter(FuncFormatter(self._money_axis))
        axis.legend(frameon=False, fontsize=8)
        self._style_axis(axis)

    def _style_axis(self, axis) -> None:
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
        axis.spines["left"].set_color("#d8dee2")
        axis.spines["bottom"].set_color("#d8dee2")
        axis.tick_params(colors="#66737c", labelsize=8)
        axis.grid(axis="y", color="#ebeff1", linewidth=0.8)
        axis.set_axisbelow(True)

    def _draw_monthly(self, axis, data: DashboardData) -> None:
        labels = [row[0] for row in data.monthly_totals]
        incomes = [float(row[1]) for row in data.monthly_totals]
        expenses = [float(row[2]) for row in data.monthly_totals]
        positions = list(range(len(labels)))
        width = 0.38

        axis.bar(
            [position - width / 2 for position in positions],
            incomes,
            width,
            label=self.profile["income"],
            color="#36b37e",
        )
        axis.bar(
            [position + width / 2 for position in positions],
            expenses,
            width,
            label=self.profile["expense"],
            color="#f06b6b",
        )
        axis.set_title("月度收支", loc="left", fontsize=11, fontweight="bold")
        axis.set_xticks(positions)
        step = max(1, len(labels) // 8)
        axis.set_xticklabels(
            [label if index % step == 0 else "" for index, label in enumerate(labels)],
            rotation=35,
            ha="right",
        )
        axis.yaxis.set_major_formatter(FuncFormatter(self._money_axis))
        axis.legend(frameon=False, fontsize=8, ncol=2, loc="upper left")
        self._style_axis(axis)

    def _draw_categories(self, axis, data: DashboardData) -> None:
        axis.set_title("支出分类", loc="left", fontsize=11, fontweight="bold")
        axis.axis("off")
        if not data.category_expenses:
            axis.text(
                0.5,
                0.5,
                "暂无支出",
                ha="center",
                va="center",
                color="#8a969e",
                transform=axis.transAxes,
            )
            return

        categories = [item[0] for item in data.category_expenses]
        amounts = [float(item[1]) for item in data.category_expenses]
        colors = [
            "#4c78a8",
            "#f58518",
            "#e45756",
            "#72b7b2",
            "#54a24b",
            "#eeca3b",
            "#b279a2",
            "#ff9da6",
            "#9d755d",
        ]
        wedges, _texts, _auto = axis.pie(
            amounts,
            startangle=90,
            counterclock=False,
            colors=colors,
            wedgeprops={"width": 0.42, "edgecolor": "white"},
            autopct=lambda percentage: f"{percentage:.0f}%" if percentage >= 6 else "",
            pctdistance=0.78,
            textprops={"fontsize": 8, "color": "#34444f"},
        )
        axis.legend(
            wedges,
            categories,
            loc="center left",
            bbox_to_anchor=(0.92, 0.5),
            frameon=False,
            fontsize=8,
        )

    def _draw_trend(self, axis, data: DashboardData) -> None:
        dates = [item[0] for item in data.balance_trend]
        balances = [float(item[1]) for item in data.balance_trend]
        line_color = "#3478c0"

        axis.plot(dates, balances, color=line_color, linewidth=2.2, marker="o", markersize=4)
        axis.fill_between(dates, balances, 0, color=line_color, alpha=0.10)
        axis.axhline(0, color="#9aa4ab", linewidth=0.8)
        axis.set_title("累计净现金流（所选期间）" if self.kind == "shop" else "累计结余（所选期间）", loc="left", fontsize=11, fontweight="bold")
        if len(dates) == 1:
            axis.set_xlim(dates[0] - timedelta(days=1), dates[0] + timedelta(days=1))
            axis.set_xticks(dates)
            axis.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
        axis.yaxis.set_major_formatter(FuncFormatter(self._money_axis))
        axis.tick_params(axis="x", rotation=20)
        axis.margins(x=0.02)
        self._style_axis(axis)

    def is_open(self) -> bool:
        try:
            return bool(self.window.winfo_exists())
        except tk.TclError:
            return False

    def focus(self) -> None:
        if self.is_open():
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()

    def close(self) -> None:
        if self.is_open():
            self.figure.clear()
            self.window.destroy()
