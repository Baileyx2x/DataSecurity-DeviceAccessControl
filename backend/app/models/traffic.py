"""设备流量统计 — 每次扫描收集轻量行为画像。"""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DeviceTraffic(Base):
    __tablename__ = "device_traffic"

    id:          Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id:   Mapped[int] = mapped_column(ForeignKey("device.id"), index=True)
    pkt_in:      Mapped[int] = mapped_column(BigInteger, default=0)
    pkt_out:     Mapped[int] = mapped_column(BigInteger, default=0)
    bytes_in:    Mapped[int] = mapped_column(BigInteger, default=0)
    bytes_out:   Mapped[int] = mapped_column(BigInteger, default=0)
    top_ports:       Mapped[str | None] = mapped_column(String(512), nullable=True)  # JSON [80,443,53,...]
    unique_dst_ips:   Mapped[int] = mapped_column(Integer, default=0)   # 采样期间不同目的 IP 数
    unique_dst_ports: Mapped[int] = mapped_column(Integer, default=0)   # 采样期间不同目的端口数
    sample_at:       Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
