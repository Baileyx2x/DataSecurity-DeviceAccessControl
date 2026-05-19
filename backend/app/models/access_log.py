"""接入日志 — 设备上下线 / IP 变化等事件。"""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AccessLog(Base):
    __tablename__ = "access_log"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id:  Mapped[int]      = mapped_column(ForeignKey("device.id"), index=True)
    event_type: Mapped[str]      = mapped_column(String(16))            # online / offline / ip_change
    ip:         Mapped[str]      = mapped_column(String(45))
    timestamp:  Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
