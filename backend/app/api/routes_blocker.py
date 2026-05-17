"""阻断 / 放行路由。"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..models.base import get_session
from ..models.device import Device
from ..core import blocker

router = APIRouter()


@router.post("/{device_id}/block")
def block(device_id: int, reason: str = "manual", gateway_ip: str = "",
          duration_min: int = 0, db: Session = Depends(get_session)):
    dev = db.get(Device, device_id)
    if not dev: raise HTTPException(404)
    blocked_until = None
    if duration_min > 0:
        blocked_until = datetime.utcnow() + timedelta(minutes=duration_min)
    blocker.block_device(db, dev, gateway_ip=gateway_ip, actor="user",
                         reason=reason, blocked_until=blocked_until)
    extra = {}
    if blocked_until:
        extra["blocked_until"] = blocked_until.isoformat()
    return {"status": "blocked", **extra}


@router.post("/{device_id}/unblock")
def unblock(device_id: int, reason: str = "manual", db: Session = Depends(get_session)):
    dev = db.get(Device, device_id)
    if not dev: raise HTTPException(404)
    blocker.unblock_device(db, dev, actor="user", reason=reason)
    return {"status": "released"}


@router.get("/active")
def active():
    return {"active_ids": blocker.get_active_ids()}
