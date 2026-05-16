"""告警表 — 风险引擎产生的告警事件。"""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Alert(Base):
    __tablename__ = "alert"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id:  Mapped[int]      = mapped_column(ForeignKey("device.id"), index=True)
    rule_id:    Mapped[int | None] = mapped_column(ForeignKey("rule.id"), nullable=True)
    level:      Mapped[int]      = mapped_column(Integer, default=0)            # 0~3
    message:    Mapped[str]      = mapped_column(Text)
    status:     Mapped[str]      = mapped_column(String(16), default="open")    # open/ack/closed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    rule = relationship("Rule", lazy="joined")
