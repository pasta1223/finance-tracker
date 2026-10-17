# 项目进度

当前版本：**1.2.0**。更新时间：2026-10-17。要求和验收口径见 `REQUIREMENTS.md`。

## 阶段索引

 

| 阶段 | 主题 | 结果 |
| --- | -- | -- |
| 09-10 ～ 09-17 | 项目基础 | 交易模型、CLI 和手写数据结构已有实现。 |
| 09-18 ～ 09-27 | 数据管理 | JSON 持久化、预算、导出及测试已有实现。 |
| 09-28 ～ 10-04 | 1.1.0 可视化 | Dashboard 与统计模块已完成。 |
| 10-05 ～ 10-10 | Windows 打包 | EXE 图表依赖修复已完成。 |
| 10-11 | 验证与整理 | EXE 看板打开成功、69 项测试通过；文档及文件清理完成。 |
| 10-17 | 1.2.0 完全 SQLite 与 UML | GUI/CLI、交易、预算和配置统一使用 SQLite；JSON 运行时路径已移除，72 项测试通过。 |

## 当前状态

| 项目 | 当前状态 | 依据或说明 |
| --- | --- | --- |
| CLI 交易管理、搜索、统计、导出与预算 | 已实现 | `main.py`、`src/ui/cli.py`；相关自动化测试通过。 |
| 图形界面交易新增、删除、筛选、搜索、撤销和重做 | 已实现 | `gui.py`。GUI 暂无直接修改交易的表单；修改可通过 CLI 完成。 |
| GUI 与 CLI 共用含预算的账本 | 已实现 | 两个入口均通过 `FinanceApplicationState` 访问同一 SQLite 数据库，并一起序列化交易与预算。 |
| SQLite 持久化与冲突保护 | 已实现 | `SQLiteStorage` 使用事务、WAL、忙等待和修订号检查；旧进程不能静默覆盖新提交。 |
| 完全 SQLite 持久化 | 已实现 | 交易、预算、元数据和 CLI 配置均使用 SQLite；JSON 后端、旧迁移器和数据备份生成代码已移除。 |
| 财务看板 | 已实现 | `src/ui/dashboard.py` 与 `src/services/analytics.py`；支持三种时间范围和空数据。 |
| Windows 单文件 EXE | 已实现并验证 | `财务管理系统.spec`；最终构建使用 PyInstaller 6.22.3。曾从 EXE 内自动打开 Dashboard，结果为 `ok`。 |
| 自动化测试 | 已通过 | 2026-10-17 运行 `python -m unittest discover -s tests -q`：72 项通过；已删除只验证废弃 JSON 后端/导出的测试。 |
| 家庭财务与公司流水 | 长期规划 | Use Case Diagram 已标记 `planned`；当前版本尚未实现多账本、成员权限、应收应付和公司报表。 |
| 队列在业务流程中的集成 | 待完成 | 已实现 `src/data_structures/queue.py` 并有测试，但当前业务流程未使用队列；原课程要求是“实现并集成”。 |
| EXE 在另一台 Windows 电脑上的运行验证 | 待确认 | 已在本机验证主窗口和 Dashboard；尚无另一台电脑的验证记录。 |

## 交付与数据说明

- 源码目录：`finance_tracker/`；构建产物：`finance_tracker/dist/财务管理系统.exe`。
- 源码 GUI 与 CLI 默认共用项目 `data/finance_tracker.db`；EXE 使用自身同目录的 `data/finance_tracker.db`，也可通过环境变量覆盖路径。
- 功能进度以本文件和 `CHANGELOG.md` 为准。
