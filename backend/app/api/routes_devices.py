"""设备相关路由 — 列表 / 详情 / 分类切换。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..models.base import get_session
from ..models.device import Device
from ..core import registry

router = APIRouter()

@router.get("")
def list_devices(category: str | None = None, status: str | None = None,
                 db: Session = Depends(get_session)):
    q = db.query(Device)
    if category: q = q.filter(Device.category == category)
    if status:   q = q.filter(Device.status == status)
    return [d.__dict__ for d in q.all()]

@router.get("/{device_id}")
def get_device(device_id: int, db: Session = Depends(get_session)):
    dev = db.get(Device, device_id)
    if not dev: raise HTTPException(404)
    return dev.__dict__

@router.post("/{device_id}/whitelist")
def to_whitelist(device_id: int, db: Session = Depends(get_session)):
    return registry.set_category(db, device_id, "white", actor="user").__dict__

@router.post("/{device_id}/blacklist")
def to_blacklist(device_id: int, db: Session = Depends(get_session)):
    return registry.set_category(db, device_id, "black", actor="user").__dict__
