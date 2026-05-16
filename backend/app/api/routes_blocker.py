"""阻断 / 放行路由。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..models.base import get_session
from ..models.device import Device
from ..core import blocker

router = APIRouter()

@router.post("/{device_id}/block")
def block(device_id: int, reason: str = "manual", gateway_ip: str = "",
          db: Session = Depends(get_session)):
    dev = db.get(Device, device_id)
    if not dev: raise HTTPException(404)
    blocker.block_device(db, dev, gateway_ip=gateway_ip, actor="user", reason=reason)
    return {"status": "blocked"}

@router.post("/{device_id}/unblock")
def unblock(device_id: int, reason: str = "manual", db: Session = Depends(get_session)):
    dev = db.get(Device, device_id)
    if not dev: raise HTTPException(404)
    blocker.unblock_device(db, dev, actor="user", reason=reason)
    return {"status": "released"}

@router.get("/active")
def active():
    return {"active_ids": list(blocker._active.keys())}
