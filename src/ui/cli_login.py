"""Password authentication for the developer CLI; never accepts a ledger path."""

from getpass import getpass

from ..services.auth_service import AuthService, AuthenticationError


def authenticate_cli():
    auth = AuthService()
    print("登录类型：1. 个人  2. 家庭  3. 小商铺（创建账号请使用 GUI）")
    kind = {"1": "personal", "2": "family", "3": "shop"}.get(input("选择登录类型：").strip())
    if kind is None:
        raise AuthenticationError("无效的登录类型。")
    account = input("家庭账号：" if kind == "family" else "账号：")
    username = input("家庭成员账号：") if kind == "family" else ""
    session = auth.login(kind, account, getpass("密码："), username=username)
    return auth.open_state(session)
