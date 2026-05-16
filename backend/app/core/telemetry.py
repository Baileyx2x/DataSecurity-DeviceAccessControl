"""状态采集 — 维护设备在线/离线状态,写入 access_log。"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..models.device import Device
from ..models.access_log import AccessLog


OFFLINE_THRESHOLD_SEC = 120  # 超过 N 秒未见即视为离线


def mark_online(db: Session, device_id: int, ip: str) -> None:
    db.add(AccessLog(device_id=device_id, event_type="online", ip=ip))
    db.commit()


def reap_offline(db: Session) -> int:
    """扫描所有在线设备,将 last_seen 过期的标记为 offline 并产生事件。"""
    cutoff = datetime.utcnow() - timedelta(seconds=OFFLINE_THRESHOLD_SEC)
    n = 0
    for dev in db.query(Device).filter(Device.status == "online", Device.last_seen < cutoff).all():
        dev.status = "offline"
        db.add(AccessLog(device_id=dev.id, event_type="offline", ip=dev.ip))
        n += 1
    db.commit()
    return n
