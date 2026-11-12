"""Login, registration, and invitation-based family membership forms."""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

from ..services.auth_service import AuthService, AuthenticationError
from ..version import APP_VERSION


class LoginView(ttk.Frame):
    def __init__(self, root, auth, on_login):
        super().__init__(root, padding=28)
        self.auth, self.on_login = auth, on_login
        self.pack(fill="both", expand=True)
        root.title(f"财务管理系统 v{APP_VERSION} · 登录")
        root.geometry("760x720")
        root.minsize(720, 680)
        ttk.Label(self, text="财务管理系统", font=("Microsoft YaHei", 24, "bold")).pack(pady=(8, 5))
        ttk.Label(self, text="选择登录类型，进入对应账本", foreground="#64748b").pack(pady=(0, 20))
        self.kind = tk.StringVar(value="personal")
        choices = ttk.Frame(self)
        choices.pack()
        for key, label in AuthService.KINDS.items():
            ttk.Radiobutton(choices, text=label, variable=self.kind, value=key,
                            command=self.rebuild).pack(side="left", padx=22)
        self.action = tk.StringVar(value="登录")
        self.actions = ttk.Combobox(self, textvariable=self.action, state="readonly", width=25)
        self.actions.pack(pady=18)
        self.actions.bind("<<ComboboxSelected>>", lambda _event: self.rebuild())
        self.form = ttk.Frame(self)
        self.form.pack()
        self.hint = ttk.Label(self, wraplength=620, foreground="#64748b", justify="center")
        self.hint.pack(pady=12)
        self.submit_btn = ttk.Button(self, text="登录", command=self.submit)
        self.submit_btn.pack(ipadx=60, ipady=5)
        self.bind_id = root.bind("<Return>", lambda _event: self.submit())
        self.rebuild()

    def rebuild(self):
        for child in self.form.winfo_children():
            child.destroy()
        family = self.kind.get() == "family"
        options = ["登录", "创建家庭", "加入家庭"] if family else ["登录", "注册账号"]
        self.actions["values"] = options
        if self.action.get() not in options:
            self.action.set("登录")
        action = self.action.get()
        self.fields = {}
        account_label = {"personal": "个人账号", "family": "家庭账号", "shop": "商铺账号"}[self.kind.get()]
        fields = [("account", account_label)]
        if family:
            fields.append(("username", "家庭成员账号"))
        if action in ("创建家庭", "注册账号"):
            fields.append(("name", "账本名称（可选）"))
        if action != "登录":
            fields.append(("display_name", "成员昵称（可选）" if family else "昵称（可选）"))
        if action == "加入家庭":
            fields.append(("invite", "家庭邀请码"))
        fields.append(("password", "成员密码" if family else "密码"))
        if action != "登录":
            fields.append(("confirm", "确认密码"))
        for row, (key, label) in enumerate(fields):
            ttk.Label(self.form, text=label).grid(row=row, column=0, sticky="w", padx=12, pady=7)
            entry = ttk.Entry(self.form, width=32, show="●" if key in ("password", "confirm") else "")
            entry.grid(row=row, column=1, pady=7)
            self.fields[key] = entry
        self.fields["account"].focus_set()
        self.submit_btn.configure(text=action)
        hint = "密码需为 8–128 个字符，账号需为 2–64 个字符。"
        if family:
            hint += "\n家庭账号用于选择家庭；每位成员使用自己的账号和密码。加入家庭需向管理员获取邀请码。"
        self.hint.configure(text=hint)

    def submit(self):
        values = {key: entry.get() for key, entry in self.fields.items()}
        action, kind = self.action.get(), self.kind.get()
        if action != "登录" and values["password"] != values["confirm"]:
            messagebox.showwarning("请检查密码", "两次输入的密码不一致。", parent=self)
            return
        self.submit_btn.configure(state="disabled")
        self.update_idletasks()
        session = None
        try:
            if action == "登录":
                session = self.auth.login(kind, values["account"], values["password"], username=values.get("username", ""))
            elif action == "加入家庭":
                session = self.auth.join_family(values["account"], values["invite"], values["username"],
                                                values["password"], display_name=values.get("display_name", ""))
            else:
                session = self.auth.register(kind, values["account"], values["password"],
                                             name=values.get("name", ""), username=values.get("username", ""),
                                             display_name=values.get("display_name", ""))
            self.on_login(session)
        except (AuthenticationError, sqlite3.Error, OSError) as error:
            if session:
                self.auth.logout(session)
            messagebox.showerror("登录失败", str(error), parent=self)
        finally:
            if self.winfo_exists():
                self.submit_btn.configure(state="normal")

    def destroy(self):
        self.master.unbind("<Return>", self.bind_id)
        for key in ("password", "confirm", "invite"):
            if key in self.fields:
                self.fields[key].delete(0, tk.END)
        super().destroy()
