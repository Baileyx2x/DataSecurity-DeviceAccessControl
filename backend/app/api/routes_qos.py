"""QoS 带宽限速路由。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..models.base import get_session
from ..models.device import Device
from ..config import settings
from ..core import qos
from ..utils.net import detect_interface

router = APIRouter()


def _lan_iface() -> str:
    return settings.lan_interface or detect_interface()


@router.post("/{device_id}/limit")
def limit(device_id: int, data: dict, db: Session = Depends(get_session)):
    """对设备设置带宽限制。仅 Linux 有效。"""
    dev = db.get(Device, device_id)
    if not dev:
        raise HTTPException(404)
    down = max(0, int(data.get("down_kbps", 0) or 0))
    up = max(0, int(data.get("up_kbps", 0) or 0))
    if down == 0 and up == 0:
        raise HTTPException(400, "down_kbps 和 up_kbps 不能同时为 0")
    try:
        qos.limit_device(db, dev, _lan_iface(), down_kbps=down, up_kbps=up)
    except qos.QosError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "down_kbps": down, "up_kbps": up}


@router.post("/{device_id}/unlimit")
def unlimit(device_id: int, db: Session = Depends(get_session)):
    """移除设备的带宽限制。"""
    dev = db.get(Device, device_id)
    if not dev:
        raise HTTPException(404)
    try:
        qos.remove_limit(db, dev, _lan_iface())
    except qos.QosError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@router.get("/active")
def active():
    return {"limits": qos.get_active()}
