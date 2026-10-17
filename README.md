# 个人财务跟踪系统

当前版本：**1.2.0**。

这是一个使用 SQLite 保存交易和预算的 Python 项目，包含 Tkinter 图形界面、命令行界面和财务数据看板。`1.1.0` 增加了 Dashboard 数据可视化；`1.2.0` 将 GUI 和 CLI 统一到同一个 SQLite 持久化流程，解决两个界面之间交易数据不互通的问题。项目源码位于 `finance_tracker`，Windows 单文件程序由 `财务管理系统.spec` 构建。

## 运行环境

- 已验证：Windows 11、Python 3.13.5、Tkinter 8.6、Matplotlib 3.10.8。
- 源码运行需要 Python 自带的 Tkinter；数据看板另需安装 `requirements.txt` 中的 Matplotlib。
- 重新打包需安装 `requirements-build.txt` 中的 PyInstaller 和 hooks。EXE 使用者无需安装 Python 依赖。

```powershell
cd E:\PythonProject\finance_tracker
python -m pip install -r requirements.txt
python gui.py
```

打包后的最终用户程序只提供 GUI；个人用户以及未来规划中的家庭用户和公司财务用户都不需要使用 CLI。`python main.py` 是保留给开发者测试、诊断和维护的内部命令行入口，可用 `python main.py --help` 查看测试参数。图形界面右上角的 **Dashboard** 可查看收入、支出、结余、交易数、月度收支、支出分类和累计结余；可切换最近 6 个月、最近 12 个月或全部时间。

## 数据和日志

GUI 和 CLI 现在都通过 `FinanceApplicationState` 保存完整状态，并默认访问项目目录中的同一个 SQLite 数据库：

```text
E:\PythonProject\finance_tracker\data\finance_tracker.db
```

数据库包含交易、月度预算、分类预算和应用元数据表。每次保存都在一个 SQLite 事务中提交，因此交易和预算不会再因 GUI/CLI 的序列化差异而互相覆盖。数据库还维护修订号；如果两个已打开的进程基于不同旧版本保存，较旧进程会收到冲突提示，而不是静默覆盖较新的数据。

交易、预算、应用元数据和 CLI 配置现在全部保存在该 SQLite 数据库中。运行时代码不再读取或写入任何 `.json` 文件，也不再生成 `finance_data.backup*.json`。CLI 数据导出仅提供 CSV 和 TXT 报表。源码 GUI 与 CLI 共用项目 `data` 目录；打包后的 EXE 默认使用 EXE 同目录下的 `data` 目录。可用 `FINANCE_TRACKER_DB_PATH` 指定数据库文件，或用 `FINANCE_TRACKER_DATA_DIR` 指定数据目录，便于测试和特殊部署。

`data/app.log` 是 CLI 运行日志。Dashboard 错误堆栈写入 SQLite 数据库所在目录的 `dashboard_error.log`。这些日志不作为项目更新记录；功能变更见 `CHANGELOG.md`，当前进度见 `PROGRESS.md`。

项目的长期方向还包括家庭共享财务管理和商务公司流水管理。目前只在 Use Case Diagram 中标记为 `planned`，本版本尚未实现账户隔离、成员权限、应收应付或公司报表。

## 构建 Windows EXE

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --clean .\财务管理系统.spec
```

生成文件为 `dist/财务管理系统.exe`。构建脚本收集 Matplotlib 的 TkAgg 后端和 NumPy 所需模块。构建后应从 EXE 打开 Dashboard 验证，因为主窗口启动成功不足以验证图表依赖。

## 测试与文档

```powershell
python -m unittest discover -s tests -q
```

- `REQUIREMENTS.md`：项目功能、技术要求和验收标准。
- `CHANGELOG.md`：按日期记录已经完成的变更。
- `PROGRESS.md`：当前完成情况、验证结果和待办问题。
- `docs/uml/README.md`：Context Modeling、Use Case、Class、Sequence 等 UML 图及其渲染说明。
- `.codebuddy/rules/financial_tracker.mdc`：原课程项目约束，继续供 CodeBuddy 使用。
