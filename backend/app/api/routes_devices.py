"""设备相关路由 — 列表 / 详情 / 分类切换 / 历史。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..models.base import get_session
from ..models.device import Device
from ..models.access_log import AccessLog
from ..models.alert import Alert
from ..models.audit_log import AuditLog
from ..core import registry

router = APIRouter()


@router.get("")
def list_devices(category: str | None = None, status: str | None = None,
                 db: Session = Depends(get_session)):
    q = db.query(Device)
    if category: q = q.filter(Device.category == category)
    if status:   q = q.filter(Device.status == status)
    return [d.__dict__ for d in q.order_by(Device.last_seen.desc()).all()]


@router.get("/{device_id}")
def get_device(device_id: int, db: Session = Depends(get_session)):
    dev = db.get(Device, device_id)
    if not dev: raise HTTPException(404)
    d = dev.__dict__
    # 补充关联数据量
    d["alert_count"] = db.query(Alert).filter(
        Alert.device_id == device_id, Alert.status == "open"
    ).count()
    d["access_count"] = db.query(AccessLog).filter(
        AccessLog.device_id == device_id
    ).count()
    return d


@router.get("/{device_id}/history")
def device_history(device_id: int, limit: int = 50, db: Session = Depends(get_session)):
    rows = db.query(AccessLog).filter(
        AccessLog.device_id == device_id
    ).order_by(AccessLog.id.desc()).limit(limit).all()
    return [r.__dict__ for r in rows]


@router.get("/{device_id}/alerts")
def device_alerts(device_id: int, db: Session = Depends(get_session)):
    rows = db.query(Alert).filter(
        Alert.device_id == device_id
    ).order_by(Alert.id.desc()).limit(100).all()
    return [r.__dict__ for r in rows]


@router.get("/{device_id}/audit")
def device_audit(device_id: int, limit: int = 50, db: Session = Depends(get_session)):
    rows = db.query(AuditLog).filter(
        AuditLog.target_device_id == device_id
    ).order_by(AuditLog.id.desc()).limit(limit).all()
    return [r.__dict__ for r in rows]


@router.post("/{device_id}/whitelist")
def to_whitelist(device_id: int, db: Session = Depends(get_session)):
    return registry.set_category(db, device_id, "white", actor="user").__dict__


@router.put("/{device_id}/schedule")
def set_schedule(device_id: int, data: dict, db: Session = Depends(get_session)):
    """设置设备上网时段。传空字符串清除限制。"""
    dev = db.get(Device, device_id)
    if not dev:
        raise HTTPException(404)
    start = str(data.get("block_schedule_start", "") or "").strip()
    end = str(data.get("block_schedule_end", "") or "").strip()
    dev.block_schedule_start = start or None
    dev.block_schedule_end = end or None
    db.commit()
    # 清除时段时,若设备正被时段阻断,则自动放行
    if not dev.block_schedule_start and not dev.block_schedule_end:
        if dev.status == "blocked" and dev.blocked_by == "schedule":
            from ..core import blocker as _blocker
            _blocker.unblock_device(db, dev, actor="system", reason="schedule cleared")
    return {"ok": True, "block_schedule_start": dev.block_schedule_start,
            "block_schedule_end": dev.block_schedule_end}


@router.post("/{device_id}/blacklist")
def to_blacklist(device_id: int, db: Session = Depends(get_session)):
    return registry.set_category(db, device_id, "black", actor="user").__dict__
