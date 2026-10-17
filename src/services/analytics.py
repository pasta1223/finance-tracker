"""Pure data aggregation helpers used by the graphical dashboard."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..models.transaction import Transaction, TransactionType


@dataclass(frozen=True)
class DashboardData:
    """All values required to render the dashboard."""

    transactions: Sequence[Transaction]
    total_income: Decimal
    total_expense: Decimal
    balance: Decimal
    category_expenses: Sequence[Tuple[str, Decimal]]
    monthly_totals: Sequence[Tuple[str, Decimal, Decimal]]
    balance_trend: Sequence[Tuple[datetime, Decimal]]

    @property
    def transaction_count(self) -> int:
        return len(self.transactions)


def _month_index(value: datetime) -> int:
    return value.year * 12 + value.month - 1


def _month_from_index(value: int) -> Tuple[int, int]:
    return value // 12, value % 12 + 1


def _filter_recent_months(
    transactions: Sequence[Transaction], months: Optional[int]
) -> List[Transaction]:
    """Return the latest *months* calendar months, anchored to the newest record.

    Anchoring the range to the newest transaction (instead of today's date) keeps
    historical/imported datasets useful even when no record was entered recently.
    """

    ordered = sorted(transactions, key=lambda item: item.transaction_date)
    if not ordered or months is None:
        return ordered
    if months <= 0:
        raise ValueError("months must be a positive integer or None")

    end_index = _month_index(ordered[-1].transaction_date)
    start_index = end_index - months + 1
    return [
        item
        for item in ordered
        if start_index <= _month_index(item.transaction_date) <= end_index
    ]


def build_dashboard_data(
    transactions: Iterable[Transaction], months: Optional[int] = 6
) -> DashboardData:
    """Aggregate transactions for KPI cards and dashboard charts.

    ``months=None`` includes the complete dataset. Missing calendar months are
    included in ``monthly_totals`` with zero values so the chart has a continuous
    time axis.
    """

    selected = _filter_recent_months(list(transactions), months)
    zero = Decimal("0")

    income = sum(
        (item.amount for item in selected if item.transaction_type == TransactionType.INCOME),
        zero,
    )
    expense = sum(
        (item.amount for item in selected if item.transaction_type == TransactionType.EXPENSE),
        zero,
    )

    expenses_by_category: Dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    monthly: Dict[int, List[Decimal]] = defaultdict(
        lambda: [Decimal("0"), Decimal("0")]
    )
    daily_net: Dict[datetime, Decimal] = defaultdict(lambda: Decimal("0"))

    for item in selected:
        month_key = _month_index(item.transaction_date)
        day_key = datetime.combine(item.transaction_date.date(), datetime.min.time())
        if item.transaction_type == TransactionType.INCOME:
            monthly[month_key][0] += item.amount
            daily_net[day_key] += item.amount
        elif item.transaction_type == TransactionType.EXPENSE:
            monthly[month_key][1] += item.amount
            expenses_by_category[item.category] += item.amount
            daily_net[day_key] -= item.amount

    monthly_totals: List[Tuple[str, Decimal, Decimal]] = []
    if selected:
        last_month = _month_index(selected[-1].transaction_date)
        if months is None:
            first_month = _month_index(selected[0].transaction_date)
        else:
            first_month = last_month - months + 1
        for month_key in range(first_month, last_month + 1):
            year, month = _month_from_index(month_key)
            month_income, month_expense = monthly[month_key]
            monthly_totals.append(
                (f"{year}-{month:02d}", month_income, month_expense)
            )

    running_balance = Decimal("0")
    balance_trend: List[Tuple[datetime, Decimal]] = []
    for day in sorted(daily_net):
        running_balance += daily_net[day]
        balance_trend.append((day, running_balance))

    category_expenses = sorted(
        expenses_by_category.items(), key=lambda pair: pair[1], reverse=True
    )

    return DashboardData(
        transactions=tuple(selected),
        total_income=income,
        total_expense=expense,
        balance=income - expense,
        category_expenses=tuple(category_expenses),
        monthly_totals=tuple(monthly_totals),
        balance_trend=tuple(balance_trend),
    )
