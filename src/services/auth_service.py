"""Local account authentication and routing to physically separate ledgers."""

import hashlib
import hmac
import secrets
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from ..core.paths import get_database_path
from ..exceptions.custom_exceptions import FinanceTrackerError


class AuthenticationError(FinanceTrackerError):
    """Invalid credentials, expired sessions, or denied membership."""


@dataclass(frozen=True)
class AccountSession:
    token: str
    workspace_id: str
    kind: str
    account: str
    workspace_name: str
    member_id: str
    username: str
    display_name: str
    role: str
    credential_version: int


class AuthService:
    KINDS = {"personal": "个人", "family": "家庭", "shop": "小商铺"}
    PASSWORD_ITERATIONS = 600_000

    def __init__(self, database_path=None):
        # Preserve the original database without assigning it to a new account.
        self.base_path = Path(database_path or get_database_path()).resolve()
        self.registry_path = self.base_path.with_name(self.base_path.stem + "_accounts.db")
        self.ledger_directory = self.base_path.parent / (self.base_path.stem + "_ledgers")
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._sessions = {}
        with closing(self._connect()) as connection, connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL CHECK(kind IN ('personal', 'family', 'shop')),
                    account TEXT NOT NULL,
                    name TEXT NOT NULL,
                    invite_hash TEXT,
                    UNIQUE(kind, account)
                );
                CREATE TABLE IF NOT EXISTS members (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
                    username TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('owner', 'member')),
                    credential_version INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(workspace_id, username)
                );
            """)

    def _connect(self):
        connection = sqlite3.connect(str(self.registry_path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _identifier(value, label):
        value = value.strip().casefold()
        if not 2 <= len(value) <= 64 or any(c.isspace() or c in "/\\" for c in value):
            raise AuthenticationError(f"{label}需为 2–64 个字符，不能包含空白或路径分隔符。")
        return value

    @staticmethod
    def _display_name(value, fallback):
        value = value.strip() or fallback
        if len(value) > 64:
            raise AuthenticationError("名称最多 64 个字符。")
        return value

    @staticmethod
    def _validate_password(password):
        if not 8 <= len(password) <= 128 or not password.strip():
            raise AuthenticationError("密码需为 8–128 个字符。")

    @classmethod
    def _hash_password(cls, password):
        cls._validate_password(password)
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), cls.PASSWORD_ITERATIONS)
        return f"pbkdf2_sha256${cls.PASSWORD_ITERATIONS}${salt}${digest.hex()}"

    @staticmethod
    def _check_password(password, encoded):
        try:
            algorithm, iterations, salt, expected = encoded.split("$")
            if algorithm != "pbkdf2_sha256" or len(password) > 128:
                return False
            actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
            return hmac.compare_digest(actual.hex(), expected)
        except (ValueError, TypeError):
            return False

    @classmethod
    def _validate_kind(cls, kind):
        if kind not in cls.KINDS:
            raise AuthenticationError("请选择个人、家庭或小商铺。")

    def register(self, kind, account, password, *, name="", username="", display_name=""):
        self._validate_kind(kind)
        account = self._identifier(account, "账号")
        username = self._identifier(username, "成员账号") if kind == "family" else account
        name = self._display_name(name, account)
        display_name = self._display_name(display_name, username)
        encoded = self._hash_password(password)
        workspace_id, member_id = uuid.uuid4().hex, uuid.uuid4().hex
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute("INSERT INTO workspaces(id, kind, account, name) VALUES (?, ?, ?, ?)",
                                   (workspace_id, kind, account, name))
                connection.execute("""INSERT INTO members
                    (id, workspace_id, username, display_name, password_hash, role)
                    VALUES (?, ?, ?, ?, ?, 'owner')""",
                                   (member_id, workspace_id, username, display_name, encoded))
        except sqlite3.IntegrityError:
            raise AuthenticationError("该登录类型的账号已存在，请登录或更换账号。") from None
        return self.login(kind, account, password, username=username)

    def login(self, kind, account, password, *, username=""):
        self._validate_kind(kind)
        account = self._identifier(account, "账号")
        username = self._identifier(username, "成员账号") if kind == "family" else account
        with closing(self._connect()) as connection:
            row = connection.execute("""SELECT m.*, w.kind, w.account, w.name
                FROM members m JOIN workspaces w ON m.workspace_id = w.id
                WHERE w.kind = ? AND w.account = ? AND m.username = ?""",
                                     (kind, account, username)).fetchone()
        if row is None or not self._check_password(password, row["password_hash"]):
            raise AuthenticationError("账号、成员账号或密码错误。")
        session = AccountSession(secrets.token_urlsafe(32), row["workspace_id"], row["kind"],
                                 row["account"], row["name"], row["id"], row["username"],
                                 row["display_name"], row["role"], row["credential_version"])
        self._sessions[session.token] = session
        return session

    def validate_session(self, session):
        if not isinstance(session, AccountSession) or self._sessions.get(session.token) != session:
            raise AuthenticationError("登录已失效，请重新登录。")
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT workspace_id, credential_version FROM members WHERE id = ?",
                                     (session.member_id,)).fetchone()
        if row is None or row["workspace_id"] != session.workspace_id or row["credential_version"] != session.credential_version:
            self.logout(session)
            raise AuthenticationError("密码已修改或登录已失效，请重新登录。")
        return session

    def logout(self, session):
        self._sessions.pop(session.token, None)

    def ledger_path(self, session):
        session = self.validate_session(session)
        # Filenames come only from database-generated UUIDs, never usernames.
        return self.ledger_directory / f"{session.workspace_id}.db"

    def open_state(self, session):
        from .application_state import FinanceApplicationState
        return FinanceApplicationState(str(self.ledger_path(session)), auth_service=self, session=session)

    def change_password(self, session, old_password, new_password):
        self.validate_session(session)
        encoded = self._hash_password(new_password)
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT password_hash, credential_version FROM members WHERE id = ?",
                                     (session.member_id,)).fetchone()
            if row["credential_version"] != session.credential_version or not self._check_password(old_password, row["password_hash"]):
                raise AuthenticationError("原密码错误或登录已失效。")
            connection.execute("UPDATE members SET password_hash = ?, credential_version = credential_version + 1 WHERE id = ?",
                               (encoded, session.member_id))
        self.logout(session)

    def _require_family(self, session, owner=False):
        self.validate_session(session)
        if session.kind != "family" or (owner and session.role != "owner"):
            raise AuthenticationError("只有家庭管理员可以执行此操作。" if owner else "此功能仅限家庭成员。")

    def rotate_invite(self, session):
        self._require_family(session, owner=True)
        code = secrets.token_hex(12)
        with closing(self._connect()) as connection, connection:
            connection.execute("UPDATE workspaces SET invite_hash = ? WHERE id = ?",
                               (hashlib.sha256(code.encode()).hexdigest(), session.workspace_id))
        return code

    def join_family(self, account, invite_code, username, password, *, display_name=""):
        account = self._identifier(account, "家庭账号")
        username = self._identifier(username, "成员账号")
        display_name = self._display_name(display_name, username)
        encoded = self._hash_password(password)
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute("SELECT id, invite_hash FROM workspaces WHERE kind = 'family' AND account = ?",
                                         (account,)).fetchone()
                digest = hashlib.sha256(invite_code.strip().encode()).hexdigest()
                if row is None or not row["invite_hash"] or not hmac.compare_digest(row["invite_hash"], digest):
                    raise AuthenticationError("家庭账号或邀请码错误，请向家庭管理员获取邀请码。")
                connection.execute("""INSERT INTO members
                    (id, workspace_id, username, display_name, password_hash, role)
                    VALUES (?, ?, ?, ?, ?, 'member')""",
                                   (uuid.uuid4().hex, row["id"], username, display_name, encoded))
        except sqlite3.IntegrityError:
            raise AuthenticationError("该家庭内的成员账号已存在。") from None
        return self.login("family", account, password, username=username)

    def list_members(self, session):
        self._require_family(session)
        with closing(self._connect()) as connection:
            return [dict(row) for row in connection.execute(
                "SELECT id, username, display_name, role FROM members WHERE workspace_id = ? ORDER BY role DESC, username",
                (session.workspace_id,))]
