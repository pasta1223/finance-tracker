"""Security boundaries and shared-family persistence workflows."""

import sqlite3
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from dataclasses import replace
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.models.transaction import Transaction, TransactionType
from src.services.analytics import build_dashboard_data, build_member_totals
from src.services.application_state import FinanceApplicationState
from src.services.auth_service import AuthService, AuthenticationError
from src.ui.cli import FinanceCLI
from src.ui.cli_login import authenticate_cli
from src.core.logger import Logger


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "finance.db"
        self.auth = AuthService(self.path)

    def personal(self, name="alice"):
        return self.auth.register("personal", name, "test-password")

    def family(self, name="home"):
        owner = self.auth.register("family", name, "owner-password", username="parent", display_name="家长")
        code = self.auth.rotate_invite(owner)
        member = self.auth.join_family(name, code, "child", "child-password", display_name="孩子")
        return owner, member

    def state(self, session):
        state = self.auth.open_state(session)
        state.load()
        return state

    def add(self, state, amount="100", key="same-id", category="工资", kind=TransactionType.INCOME):
        state.transaction_manager.add(Transaction(Decimal(amount), kind, category, transaction_id=key))
        self.assertTrue(state.save(), state.last_error)

    def test_accounts_use_separate_files_and_private_budgets(self):
        alice, bob = self.personal(), self.personal("bob")
        a, b = self.state(alice), self.state(bob)
        self.assertNotEqual(a.storage_path, b.storage_path)
        a.budget_manager.set_monthly_budget(2026, 11, Decimal("500"))
        self.add(a, "123")
        self.add(b, "987")  # The same transaction ID is allowed in separate ledgers.
        a.reload()
        b.reload()
        self.assertEqual(a.transaction_manager.get_balance(), Decimal("123"))
        self.assertEqual(b.transaction_manager.get_balance(), Decimal("987"))
        self.assertIsNone(b.budget_manager.get_monthly_budget(2026, 11))
        self.assertEqual(a.transaction_manager.find_by_id("same-id").author_id, alice.member_id)

    def test_login_persists_and_types_have_separate_namespaces(self):
        personal = self.personal("same")
        shop = self.auth.register("shop", "same", "shop-password")
        family = self.auth.register("family", "same", "home-password", username="parent")
        self.assertEqual(len({self.auth.ledger_path(s) for s in (personal, shop, family)}), 3)
        restarted = AuthService(self.path)
        session = restarted.login("personal", " SAME ", "test-password")
        self.assertEqual(restarted.ledger_path(session), self.auth.ledger_path(personal))
        with self.assertRaises(AuthenticationError):
            self.auth.login("shop", "same", "test-password")

    def test_passwords_are_salted_and_never_stored_as_plaintext(self):
        self.personal()
        self.personal("bob")
        with closing(sqlite3.connect(self.auth.registry_path)) as connection:
            hashes = [row[0] for row in connection.execute("SELECT password_hash FROM members")]
        self.assertNotEqual(*hashes)
        self.assertTrue(all(h.startswith("pbkdf2_sha256$") for h in hashes))
        self.assertNotIn(b"test-password", self.auth.registry_path.read_bytes())

    def test_duplicate_invalid_accounts_and_wrong_credentials_are_rejected(self):
        self.personal()
        for kind, name, password in (("personal", " ALICE ", "another-password"),
                                      ("personal", "../escape", "some-password"),
                                      ("personal", "short", "123"),
                                      ("unknown", "name", "some-password")):
            with self.subTest(kind=kind, name=name), self.assertRaises(AuthenticationError):
                self.auth.register(kind, name, password)
        with self.assertRaises(AuthenticationError):
            self.auth.login("personal", "alice", "wrong-password")
        with self.assertRaises(AuthenticationError):
            self.auth.login("family", "alice", "test-password", username="alice")

    def test_family_members_share_ledger_with_author_attribution(self):
        owner, member = self.family()
        parent, child = self.state(owner), self.state(member)
        self.assertEqual(parent.storage_path, child.storage_path)
        self.add(parent, "500", "parent-record")
        child.reload()
        self.add(child, "30", "child-record", kind=TransactionType.EXPENSE)
        parent.reload()
        self.assertEqual(parent.transaction_manager.transaction_count, 2)
        self.assertEqual(parent.transaction_manager.find_by_id("parent-record").author_id, owner.member_id)
        self.assertEqual(parent.transaction_manager.find_by_id("child-record").author_id, member.member_id)
        self.assertEqual(build_dashboard_data(parent.transaction_manager.find_all()).balance, Decimal("470"))
        other = self.auth.register("family", "other-home", "other-password", username="parent")
        self.assertNotEqual(self.auth.ledger_path(other), self.auth.ledger_path(owner))
        self.assertEqual(self.state(other).transaction_manager.transaction_count, 0)

    def test_shared_budgets_persist_without_affecting_personal_account(self):
        owner, member = self.family()
        parent = self.state(owner)
        parent.budget_manager.set_monthly_budget(2026, 11, Decimal("2000"))
        parent.budget_manager.set_category_budget("餐饮", 2026, 11, Decimal("500"))
        self.assertTrue(parent.save())
        child = self.state(member)
        self.assertEqual(child.budget_manager.get_monthly_budget(2026, 11), Decimal("2000"))
        self.add(child, "25", "food", "餐饮", TransactionType.EXPENSE)
        parent.reload()
        self.assertEqual(parent.budget_manager.get_category_budget("餐饮", 2026, 11).amount, Decimal("500"))
        self.assertIsNone(self.state(self.personal()).budget_manager.get_monthly_budget(2026, 11))

    def test_family_join_requires_current_invitation_and_owner_role(self):
        owner, member = self.family()
        old_code = self.auth.rotate_invite(owner)
        new_code = self.auth.rotate_invite(owner)
        with self.assertRaises(AuthenticationError):
            self.auth.join_family("home", old_code, "outsider", "outsider-password")
        with self.assertRaises(AuthenticationError):
            self.auth.join_family("absent-home", new_code, "outsider", "outsider-password")
        with self.assertRaises(AuthenticationError):
            self.auth.rotate_invite(member)
        with self.assertRaises(AuthenticationError):
            self.auth.join_family("home", new_code, "child", "new-password")
        self.assertEqual(len(self.auth.list_members(owner)), 2)
        with self.assertRaises(AuthenticationError):
            self.auth.list_members(self.personal())

    def test_forged_and_logged_out_sessions_cannot_open_or_save(self):
        alice, bob = self.personal(), self.personal("bob")
        with self.assertRaises(AuthenticationError):
            self.auth.open_state(replace(alice, workspace_id=bob.workspace_id))
        with self.assertRaises(AuthenticationError):
            self.auth.open_state(replace(alice, role="member"))
        state = self.state(alice)
        self.auth.logout(alice)
        with self.assertRaises(AuthenticationError):
            state.load()
        with self.assertRaises(AuthenticationError):
            state.save()

    def test_authenticated_state_rejects_a_different_ledger_path(self):
        alice, bob = self.personal(), self.personal("bob")
        wrong = FinanceApplicationState(str(self.auth.ledger_path(bob)), auth_service=self.auth, session=alice)
        with self.assertRaises(AuthenticationError):
            wrong.load()

    def test_password_change_revokes_sessions_in_other_processes(self):
        session = self.personal()
        another_auth = AuthService(self.path)
        other_session = another_auth.login("personal", "alice", "test-password")
        self.auth.change_password(session, "test-password", "replacement-password")
        with self.assertRaises(AuthenticationError):
            another_auth.open_state(other_session)
        with self.assertRaises(AuthenticationError):
            self.auth.login("personal", "alice", "test-password")
        replacement = self.auth.login("personal", "alice", "replacement-password")
        self.assertEqual(replacement.workspace_id, session.workspace_id)

    def test_wrong_old_password_and_invalid_new_password_do_not_change_credentials(self):
        session = self.personal()
        for old, new in (("wrong", "replacement-password"), ("test-password", "short")):
            with self.assertRaises(AuthenticationError):
                self.auth.change_password(session, old, new)
        self.auth.validate_session(session)
        self.auth.login("personal", "alice", "test-password")

    def test_member_cannot_modify_other_members_records_even_through_service(self):
        owner, member = self.family()
        parent = self.state(owner)
        self.add(parent)
        child = self.state(member)
        child.transaction_manager.find_by_id("same-id").description = "tampered"
        with self.assertRaises(AuthenticationError):
            child.save()
        self.assertEqual(child.transaction_manager.find_by_id("same-id").description, "")
        child.transaction_manager.remove("same-id")
        with self.assertRaises(AuthenticationError):
            child.save()
        self.assertEqual(child.transaction_manager.transaction_count, 1)

    def test_new_record_cannot_spoof_another_author_and_undo_retains_authorship(self):
        owner, member = self.family()
        child = self.state(member)
        child.transaction_manager.add(Transaction(Decimal("15"), TransactionType.EXPENSE, "食品",
            transaction_id="record", author_id=owner.member_id, author_name="假冒"))
        self.assertTrue(child.save())
        self.assertEqual(child.transaction_manager.find_by_id("record").author_id, member.member_id)
        child.transaction_manager.remove("record")
        self.assertTrue(child.save())
        self.assertTrue(child.transaction_manager.undo())
        self.assertTrue(child.save())
        self.assertEqual(child.transaction_manager.find_by_id("record").author_id, member.member_id)

    def test_concurrent_family_writes_reject_stale_snapshot(self):
        owner, member = self.family()
        parent = self.state(owner)
        self.add(parent, key="seed")
        child = self.state(member)
        self.add(parent, key="parent")
        child.transaction_manager.add(Transaction(Decimal("5"), TransactionType.EXPENSE, "食品"))
        self.assertFalse(child.save())
        self.assertIn("another process", child.last_error)
        child.reload()
        self.assertEqual(child.transaction_manager.transaction_count, 2)

    def test_original_ledger_is_preserved_and_never_assigned_to_registrant(self):
        old = FinanceApplicationState(str(self.path))
        self.add(old, "900", "legacy")
        original = self.path.read_bytes()
        session = self.personal()
        self.assertEqual(self.state(session).transaction_manager.transaction_count, 0)
        self.assertEqual(self.path.read_bytes(), original)

    def test_member_totals_group_by_id_even_when_names_are_identical(self):
        records = [Transaction(Decimal("10"), TransactionType.INCOME, "工资", author_id="one", author_name="同名"),
                   Transaction(Decimal("20"), TransactionType.EXPENSE, "餐饮", author_id="two", author_name="同名")]
        totals = {row[0]: row[2:] for row in build_member_totals(records)}
        self.assertEqual(totals, {"one": (Decimal("10"), Decimal(0)), "two": (Decimal(0), Decimal("20"))})

    def test_cli_authentication_selects_only_logged_in_ledger(self):
        session = self.personal()
        with patch("src.ui.cli_login.AuthService", return_value=self.auth), \
             patch("builtins.input", side_effect=["1", "alice"]), \
             patch("src.ui.cli_login.getpass", return_value="test-password"), redirect_stdout(StringIO()):
            state = authenticate_cli()
        self.assertEqual(state.storage_path, str(self.auth.ledger_path(session)))
        with patch("src.ui.cli.authenticate_cli", return_value=state) as login, redirect_stdout(StringIO()):
            cli = FinanceCLI(quiet=True)
        login.assert_called_once()
        self.assertIs(cli._state, state)

    def test_cli_financial_logs_are_separate_for_each_account(self):
        startup_path = Path(self.temp.name) / "startup.log"
        startup = Logger("AccountTest_" + Path(self.temp.name).name, str(startup_path))
        with redirect_stdout(StringIO()):
            alice = FinanceCLI(state=self.state(self.personal()), logger=startup, quiet=True)
            bob = FinanceCLI(state=self.state(self.personal("bob")), logger=startup, quiet=True)
        self.addCleanup(self.close_logger, startup)
        self.addCleanup(self.close_logger, alice._logger)
        self.addCleanup(self.close_logger, bob._logger)
        alice._log("PRIVATE_ALICE")
        bob._log("PRIVATE_BOB")
        a = Path(alice._state.storage_path).with_suffix(".log").read_text(encoding="utf-8")
        b = Path(bob._state.storage_path).with_suffix(".log").read_text(encoding="utf-8")
        self.assertIn("PRIVATE_ALICE", a)
        self.assertNotIn("PRIVATE_BOB", a)
        self.assertIn("PRIVATE_BOB", b)
        self.assertNotIn("PRIVATE_ALICE", b)
        self.assertNotIn("PRIVATE_", startup_path.read_text(encoding="utf-8"))

    @staticmethod
    def close_logger(logger):
        for handler in logger._logger.handlers[:]:
            handler.close()
            logger._logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
