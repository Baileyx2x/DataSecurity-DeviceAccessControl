"""统一日志 — loguru。"""
from loguru import logger
from ..config import settings

logger.remove()
logger.add(lambda m: print(m, end=""), level=settings.log_level)

__all__ = ["logger"]
