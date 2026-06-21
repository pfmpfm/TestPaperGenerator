"""
日志配置模块
"""
import sys
from pathlib import Path
from loguru import logger

from app.core.config import settings

# 移除默认的日志处理器
logger.remove()


def setup_logging():
    """配置日志系统"""

    # 日志格式
    if settings.log_format == "json":
        log_format = (
            "{{"
            '"time": "{time:YYYY-MM-DD HH:mm:ss.SSS}", '
            '"level": "{level}", '
            '"module": "{module}", '
            '"function": "{function}", '
            '"line": {line}, '
            '"message": "{message}"'
            "}}"
        )
    else:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # 控制台输出
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=settings.log_format != "json",
        backtrace=True,
        diagnose=settings.debug,
    )

    # 文件输出
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 所有日志
    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        format=log_format,
        level=settings.log_level,
        rotation="00:00",  # 每天午夜轮转
        retention="30 days",  # 保留30天
        compression="zip",  # 压缩旧日志
        encoding="utf-8",
        backtrace=True,
        diagnose=settings.debug,
    )

    # 错误日志单独记录
    logger.add(
        log_dir / "error_{time:YYYY-MM-DD}.log",
        format=log_format,
        level="ERROR",
        rotation="00:00",
        retention="90 days",  # 错误日志保留90天
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )

    # Agent执行日志
    logger.add(
        log_dir / "agent_{time:YYYY-MM-DD}.log",
        format=log_format,
        level="INFO",
        rotation="100 MB",  # 按大小轮转
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        filter=lambda record: "agent" in record["extra"],
    )

    # LLM调用日志
    logger.add(
        log_dir / "llm_{time:YYYY-MM-DD}.log",
        format=log_format,
        level="DEBUG",
        rotation="100 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
        filter=lambda record: "llm" in record["extra"],
    )

    logger.info(f"日志系统已初始化 | 级别: {settings.log_level} | 格式: {settings.log_format}")


# 导出logger实例
__all__ = ["logger", "setup_logging"]
