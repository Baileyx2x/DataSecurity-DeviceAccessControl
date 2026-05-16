"""审计日志 — 所有写操作必须经此模块落盘,便于追溯。"""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id:               Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor:            Mapped[str]      = mapped_column(String(64))         # system / 用户名
    action:           Mapped[str]      = mapped_column(String(32), index=True)
    target_device_id: Mapped[int | None] = mapped_column(ForeignKey("device.id"), nullable=True)
    reason:           Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp:        Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
