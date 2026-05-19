"""设备资产表 — 系统的核心实体。"""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Device(Base):
    __tablename__ = "device"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    mac:        Mapped[str]      = mapped_column(String(17), unique=True, index=True)
    ip:         Mapped[str]      = mapped_column(String(45), index=True)        # IPv4/IPv6
    hostname:   Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor:     Mapped[str | None] = mapped_column(String(128), nullable=True)
    os_guess:   Mapped[str | None] = mapped_column(String(64),  nullable=True)
    category:   Mapped[str]      = mapped_column(String(16), default="unknown")  # white/black/unknown
    risk_level: Mapped[int]      = mapped_column(Integer, default=0)             # 0~3
    status:     Mapped[str]      = mapped_column(String(16), default="offline")  # online/offline/blocked
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_seen:  Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # 定时阻断到期
    block_schedule_start: Mapped[str | None] = mapped_column(String(5), nullable=True)  # "HH:MM" 上网时段起始
    block_schedule_end:   Mapped[str | None] = mapped_column(String(5), nullable=True)  # "HH:MM" 上网时段结束
    blocked_by:           Mapped[str | None] = mapped_column(String(16), nullable=True)  # manual / schedule / auto
    note:       Mapped[str | None] = mapped_column(Text, nullable=True)
