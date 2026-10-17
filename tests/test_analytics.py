"""Tests for the data aggregation behind the graphical dashboard."""

import os
import sys
import unittest
from datetime import datetime
from decimal import Decimal

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.models.transaction import Transaction, TransactionType
from src.services.analytics import build_dashboard_data


def transaction(amount, kind, category, date):
    return Transaction(
        amount=Decimal(amount),
        transaction_type=kind,
        category=category,
        transaction_date=datetime.fromisoformat(date),
    )


class TestDashboardAnalytics(unittest.TestCase):
    def setUp(self):
        self.transactions = [
            transaction("5000", TransactionType.INCOME, "Salary", "2025-01-02"),
            transaction("300", TransactionType.EXPENSE, "Food", "2025-01-03"),
            transaction("1000", TransactionType.EXPENSE, "Rent", "2025-03-01"),
            transaction("5200", TransactionType.INCOME, "Salary", "2025-04-02"),
            transaction("450", TransactionType.EXPENSE, "Food", "2025-04-05"),
        ]

    def test_all_time_aggregation(self):
        data = build_dashboard_data(self.transactions, months=None)

        self.assertEqual(data.total_income, Decimal("10200"))
        self.assertEqual(data.total_expense, Decimal("1750"))
        self.assertEqual(data.balance, Decimal("8450"))
        self.assertEqual(data.transaction_count, 5)
        self.assertEqual(data.category_expenses[0], ("Rent", Decimal("1000")))
        self.assertEqual([row[0] for row in data.monthly_totals], [
            "2025-01", "2025-02", "2025-03", "2025-04"
        ])
        self.assertEqual(data.monthly_totals[1][1:], (Decimal("0"), Decimal("0")))

    def test_recent_period_is_anchored_to_latest_record(self):
        data = build_dashboard_data(self.transactions, months=2)

        self.assertEqual(data.transaction_count, 3)
        self.assertEqual(data.total_income, Decimal("5200"))
        self.assertEqual(data.total_expense, Decimal("1450"))
        self.assertEqual([row[0] for row in data.monthly_totals], ["2025-03", "2025-04"])

    def test_balance_trend_groups_records_by_day(self):
        data = build_dashboard_data(self.transactions, months=None)

        self.assertEqual(data.balance_trend[-1][1], Decimal("8450"))
        self.assertEqual(len(data.balance_trend), 5)

    def test_empty_data(self):
        data = build_dashboard_data([], months=6)

        self.assertEqual(data.transaction_count, 0)
        self.assertEqual(data.balance, Decimal("0"))
        self.assertEqual(data.monthly_totals, ())


if __name__ == "__main__":
    unittest.main()
