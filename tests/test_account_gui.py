"""Real Tk/Matplotlib flows for account switching and family records."""

import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from gui import FinanceDesktop
from src.services.auth_service import AuthService


class AccountGUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = tk.Tk()
        self.root.withdraw()
        self.desktop = FinanceDesktop(self.root, AuthService(Path(self.temp.name) / "finance.db"))
        self.error = self.enterContext(patch("tkinter.messagebox.showerror"))
        self.enterContext(patch("tkinter.messagebox.showinfo"))
        self.enterContext(patch("tkinter.messagebox.askyesno", return_value=True))
        self.addCleanup(self._close)

    def _close(self):
        self.root.update_idletasks()
        self.desktop.close()

    def register_from_form(self, kind, account, username=""):
        view = self.desktop.view
        view.kind.set(kind)
        view.rebuild()
        view.action.set("创建家庭" if kind == "family" else "注册账号")
        view.rebuild()
        for key, value in {"account": account, "username": username, "password": "gui-password", "confirm": "gui-password"}.items():
            if key in view.fields:
                view.fields[key].insert(0, value)
        view.submit()
        self.error.assert_not_called()
        self.assertIsNone(self.desktop.view)
        return self.desktop.app

    def add_from_form(self, app, amount, key):
        app.amount_entry.insert(0, amount)
        app.id_entry.insert(0, key)
        app.add_transaction()
        self.error.assert_not_called()

    def test_register_all_modes_and_render_their_dashboards(self):
        for kind in ("personal", "family", "shop"):
            with self.subTest(kind=kind):
                app = self.register_from_form(kind, "gui-" + kind, "parent")
                self.assertEqual(app.kind, kind)
                app.open_dashboard()  # Also verify empty chart handling.
                self.error.assert_not_called()
                self.add_from_form(app, "123.45", "001")
                app.dashboard.canvas.draw()
                self.assertEqual(len(app.dashboard.figure.axes), 4 if kind == "family" else 3)
                self.assertEqual(app.dashboard._kpi_values["income"]["text"], "¥123.45")
                for period in app.dashboard.PERIODS:
                    app.dashboard.period_var.set(period)
                    app.dashboard.refresh()
                app.dashboard.canvas.draw()
                old_dashboard = app.dashboard
                self.desktop.logout()
                self.assertFalse(old_dashboard.is_open())
                self.assertEqual(app.manager.transaction_count, 0)
                self.assertIsNotNone(self.desktop.view)

    def test_switching_accounts_clears_records_search_and_undo_history(self):
        app = self.register_from_form("personal", "alice")
        self.add_from_form(app, "40", "001")
        app.search_id_entry.insert(0, "001")
        app.search_by_id()
        self.assertEqual(app.tree.get_children(), ("001",))
        app.tree.selection_set("001")
        app.delete_selected()
        self.assertEqual(app.tree.get_children(), ())
        app.undo_action()
        self.assertEqual(app.tree.get_children(), ("001",))
        self.desktop.logout()
        other = self.register_from_form("personal", "bob")
        self.assertEqual(other.tree.get_children(), ())
        self.assertFalse(other.manager.can_undo())
        self.assertEqual(other.search_id_entry.get(), "")

    def test_family_join_login_member_filter_and_shared_budget(self):
        parent = self.register_from_form("family", "gui-home", "parent")
        self.add_from_form(parent, "200", "parent-record")
        parent.open_budgets()
        from src.ui.budget_panel import BudgetPanel
        panel = next(widget for window in self.root.winfo_children() if isinstance(window, tk.Toplevel)
                     for content in window.winfo_children() for widget in content.winfo_children()
                     if isinstance(widget, BudgetPanel))
        panel.amount.set("500")
        panel.save()
        invite = self.desktop.auth.rotate_invite(self.desktop.session)
        self.desktop.logout()
        view = self.desktop.view
        view.kind.set("family")
        view.rebuild()
        view.action.set("加入家庭")
        view.rebuild()
        for key, value in {"account": "gui-home", "username": "child", "invite": invite,
                           "password": "child-password", "confirm": "child-password"}.items():
            view.fields[key].insert(0, value)
        view.submit()
        self.error.assert_not_called()

        child = self.desktop.app
        self.assertEqual(child.tree.get_children(), ("parent-record",))
        self.assertIn("500.00", child.budget_label["text"])
        self.add_from_form(child, "30", "child-record")
        choice = next(label for label in child._member_choices if label.startswith("child"))
        child.member_filter.set(choice)
        child.refresh_transaction_list()
        self.assertEqual(child.tree.get_children(), ("child-record",))
        self.desktop.logout()
        session = self.desktop.auth.login("family", "gui-home", "gui-password", username="parent")
        self.desktop.login(session)
        self.assertEqual(len(self.desktop.app.tree.get_children()), 2)
        self.error.assert_not_called()

    def test_external_family_commit_refreshes_open_records_and_dashboard(self):
        parent = self.register_from_form("family", "live-home", "parent")
        parent.open_dashboard()
        invite = self.desktop.auth.rotate_invite(self.desktop.session)
        child = self.desktop.auth.join_family("live-home", invite, "child", "child-password")
        other = self.desktop.auth.open_state(child)
        other.load()
        from src.models.transaction import Transaction, TransactionType
        from decimal import Decimal
        other.transaction_manager.add(Transaction(Decimal("55"), TransactionType.INCOME, "收入", transaction_id="remote"))
        self.assertTrue(other.save())
        parent.root.after_cancel(parent._poll_id)
        parent._poll_changes()
        self.assertEqual(parent.tree.get_children(), ("remote",))
        self.assertEqual(parent.dashboard._kpi_values["income"]["text"], "¥55.00")
        self.assertFalse(parent.manager.can_undo())
        self.error.assert_not_called()

    def test_corrupt_account_ledger_keeps_login_page_without_partial_workspace(self):
        auth = self.desktop.auth
        session = auth.register("personal", "broken", "gui-password")
        path = auth.ledger_path(session)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"not a SQLite database")
        auth.logout(session)
        view = self.desktop.view
        for key, value in {"account": "broken", "password": "gui-password"}.items():
            view.fields[key].insert(0, value)
        view.submit()
        self.error.assert_called_once()
        self.assertIs(self.desktop.view, view)
        self.assertIsNone(self.desktop.app)
        self.assertEqual(self.root.winfo_children(), [view])


if __name__ == "__main__":
    unittest.main()
