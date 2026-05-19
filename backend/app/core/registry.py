"""设备登记 — 白名单 / 黑名单 / 未知三态管理 + 自动分类。"""

from datetime import datetime
from sqlalchemy.orm import Session

from ..models.device import Device
from ..utils.logger import logger
from .audit import write_audit


# 厂商自动白名单: OUI 包含以下关键词的设备首次发现时自动归为 white
AUTO_WHITE_VENDORS = [
    "apple", "samsung", "xiaomi", "huawei", "oppo", "vivo",
    "google", "microsoft", "intel", "dell", "lenovo", "hp",
    "sony", "nintendo", "amazon",
]
# MAC 前缀自动白名单 (手动补)
AUTO_WHITE_MAC_PREFIXES: list[str] = []
# MAC 前缀自动黑名单
AUTO_BLACK_MAC_PREFIXES: list[str] = []


def _auto_classify(vendor: str | None) -> str | None:
    if not vendor:
        return None
    vl = vendor.lower()
    for kw in AUTO_WHITE_VENDORS:
        if kw in vl:
            return "white"
    return None


def upsert_device(db: Session, mac: str, ip: str, **extra) -> Device:
    """根据 MAC 查找设备,存在则更新 last_seen,不存在则新建为 unknown。"""
    dev = db.query(Device).filter(Device.mac == mac).first()
    now = datetime.now()
    if dev is None:
        vendor = extra.get("vendor")
        auto_cat = _auto_classify(vendor)
        category = auto_cat or "unknown"
        dev = Device(mac=mac, ip=ip, first_seen=now, last_seen=now,
                     status="online", category=category, **extra)
        db.add(dev)
        db.flush()
        reason = f"new mac={mac}"
        if auto_cat:
            reason += f" auto_{auto_cat}(vendor={vendor})"
            logger.info(f"[registry] auto-classified: {mac} → {auto_cat}")
        write_audit(db, actor="system", action="device_discovered",
                    target_device_id=dev.id, reason=reason)
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

    # 切换为白名单/未知时,若设备是被规则自动阻断的,则自动放行
    if category in ("white", "unknown") and dev.status == "blocked" and dev.blocked_by == "auto":
        from . import blocker as _blocker
        _blocker.unblock_device(db, dev, actor="system", reason=f"category changed to {category}")
        logger.info(f"[registry] auto-unblocked {dev.ip}: category → {category}")
    return dev
