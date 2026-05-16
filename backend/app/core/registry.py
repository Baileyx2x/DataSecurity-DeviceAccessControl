"""设备登记 — 白名单 / 黑名单 / 未知三态管理。"""

from datetime import datetime
from sqlalchemy.orm import Session

from ..models.device import Device
from .audit import write_audit


def upsert_device(db: Session, mac: str, ip: str, **extra) -> Device:
    """根据 MAC 查找设备,存在则更新 last_seen,不存在则新建为 unknown。"""
    dev = db.query(Device).filter(Device.mac == mac).first()
    now = datetime.utcnow()
    if dev is None:
        dev = Device(mac=mac, ip=ip, first_seen=now, last_seen=now, status="online", **extra)
        db.add(dev)
        db.flush()
        write_audit(db, actor="system", action="device_discovered", target_device_id=dev.id, reason=f"new mac={mac}")
    else:
        dev.ip = ip
        dev.last_seen = now
        dev.status = "online"
        for k, v in extra.items():
            if v is not None:
                setattr(dev, k, v)
    db.commit()
    return dev


def set_category(db: Session, device_id: int, category: str, actor: str = "user", reason: str | None = None) -> Device:
    assert category in ("white", "black", "unknown")
    dev = db.get(Device, device_id)
    if not dev:
        raise ValueError("device not found")
    dev.category = category
    db.commit()
    write_audit(db, actor=actor, action=f"set_category:{category}", target_device_id=dev.id, reason=reason)
    return dev
