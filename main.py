"""
个人财务跟踪系统 - 主程序入口
功能完整、可持久化存储的Python软件系统
作者：Finance Tracker Team
版本：1.3.0
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core import (
    ConfigManager,
    ArgumentParser,
    LogLevel,
    Logger,
    init_logger,
    get_database_path,
)
from src.ui.cli import FinanceCLI
from src.exceptions.custom_exceptions import FinanceTrackerError


def configure_console_encoding() -> None:
    """Use UTF-8 for CLI output, including redirected output on Windows."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            # Some embedded/test streams cannot be reconfigured.
            pass


def main():
    """程序入口点"""
    configure_console_encoding()

    # 解析命令行参数
    parser = ArgumentParser()
    args = parser.parse()
    
    # 处理版本请求
    if args.version:
        parser.print_version()
        return 0
    
    # 初始化配置
    config = ConfigManager()
    
    # 初始化日志
    logger = init_logger(config)
    
    # 处理配置操作
    if args.show_config:
        print("\n=== 当前配置 ===")
        cfg = config.config
        print(f"应用名称: {cfg.app_name}")
        print(f"应用版本: {cfg.app_version}")
        print(f"SQLite 数据库: {get_database_path()}")
        print(f"日志级别: {cfg.log_level}")
        print(f"自动保存: {cfg.auto_save}")
        print(f"货币符号: {cfg.currency_symbol}")
        print(f"月度预算: {cfg.monthly_budget}")
        print("=" * 30)
        return 0
    
    if args.reset_config:
        config.reset_to_default()
        print("[成功] 配置已重置为默认值")
        return 0
    
    # 安静模式设置日志级别
    if args.quiet:
        logger.set_level(LogLevel.WARNING)
    
    # 调试模式
    if args.debug:
        logger.set_level(LogLevel.DEBUG)
        print("[调试] 调试模式已启用")
    
    logger.info("=" * 50)
    logger.info("个人财务跟踪系统启动")
    logger.info("=" * 50)
    
    # 创建应用实例
    try:
        app = FinanceCLI(config=config, logger=logger, quiet=args.quiet)
    except (FinanceTrackerError, EOFError, KeyboardInterrupt) as error:
        print(f"[错误] 未能登录: {error}")
        return 1
    account_logger = getattr(app, "_logger", None)
    if isinstance(account_logger, Logger):
        logger = account_logger
    
    # 命令行模式
    if args.add_transaction or args.list_transactions or args.search or args.export or getattr(args, 'stat', False):
        return run_command_mode(app, args, logger)
    
    # 交互模式
    try:
        app.run()
        return 0
    except KeyboardInterrupt:
        print("\n\n[提示] 用户中断程序")
        return 130
    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
        print(f"[错误] 程序异常: {e}")
        return 1


def run_command_mode(app: FinanceCLI, args, logger) -> int:
    """命令行模式执行"""
    try:
        app._state._authorize()
        # 添加交易记录
        if args.add_transaction:
            logger.info("命令行模式: 添加交易")
            app._cli_add_transaction_interactive()
        
        # 列出所有记录
        if args.list_transactions:
            logger.info("命令行模式: 列出交易")
            app._cli_list_transactions(
                start_date=args.start_date,
                end_date=args.end_date,
                category=args.category,
                transaction_type=args.transaction_type
            )
        
        # 搜索记录
        if args.search:
            logger.info(f"命令行模式: 搜索 '{args.search}'")
            results = app._manager.search(
                lambda t: args.search.lower() in str(t).lower()
            )
            print(f"\n找到 {len(results)} 条记录:")
            for t in results:
                print(f"  {t}")
        
        # 统计信息
        if getattr(args, 'stat', False):
            logger.info("命令行模式: 显示统计")
            app._cli_show_statistics()
        
        # 导出数据
        if args.export:
            logger.info(f"命令行模式: 导出到 {args.export}")
            success = app.export_data(args.export, args.export_format)
            if success:
                print(f"[成功] 数据已导出到 {args.export}")
            else:
                print("[错误] 导出失败")
                return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"命令行模式执行失败: {e}", exc_info=True)
        print(f"[错误] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
