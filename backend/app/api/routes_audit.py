"""审计日志路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..models.base import get_session
from ..models.audit_log import AuditLog
from ..models.device import Device

router = APIRouter()

@router.get("")
def list_audit(limit: int = 200, db: Session = Depends(get_session)):
    rows = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
    result = []
    for r in rows:
        d = r.__dict__
        if r.target_device_id:
            dev = db.get(Device, r.target_device_id)
            d["device_name"] = dev.name if dev else None
        else:
            d["device_name"] = None
        result.append(d)
    return result
