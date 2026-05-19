"""统计路由 — Dashboard 趋势数据。"""
from datetime import datetime, timedelta
from collections import Counter
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models.base import get_session
from ..models.device import Device
from ..models.alert import Alert
from ..models.access_log import AccessLog
from ..models.traffic import DeviceTraffic

router = APIRouter()


@router.get("/timeline")
def timeline(db: Session = Depends(get_session)):
    """返回最近 24h 每小时设备上线/告警/阻断数,供趋势图使用。"""
    now = datetime.now()
    hours = []
    alerts_by_hour: dict[int, int] = {}
    devices_by_hour: dict[int, int] = {}

    # 统计最近 24h 告警按小时分布
    cutoff = now - timedelta(hours=24)
    alerts = db.query(Alert).filter(Alert.created_at >= cutoff).all()
    for a in alerts:
        h = a.created_at.hour
        alerts_by_hour[h] = alerts_by_hour.get(h, 0) + 1

    # 统计最近 24h 设备上线分布
    logs = db.query(AccessLog).filter(
        AccessLog.timestamp >= cutoff, AccessLog.event_type == "online"
    ).all()
    for log in logs:
        h = log.timestamp.hour
        devices_by_hour[h] = devices_by_hour.get(h, 0) + 1

    for i in range(24):
        slot = (now - timedelta(hours=23 - i))
        h = slot.hour
        hours.append({
            "label": slot.strftime("%H:%M"),
            "alerts": alerts_by_hour.get(h, 0),
            "online": devices_by_hour.get(h, 0),
        })

    return hours


@router.get("/overview")
def overview(db: Session = Depends(get_session)):
    """返回当前统计概览。"""
    total = db.query(func.count(Device.id)).scalar() or 0
    online = db.query(Device).filter(Device.status == "online").count()
    blocked = db.query(Device).filter(Device.status == "blocked").count()
    open_alerts = db.query(Alert).filter(Alert.status == "open").count()
    white = db.query(Device).filter(Device.category == "white").count()
    black = db.query(Device).filter(Device.category == "black").count()

    # 最近流量总量
    traffic = db.query(
        func.sum(DeviceTraffic.bytes_in),
        func.sum(DeviceTraffic.bytes_out),
    ).first()

    return {
        "total": total, "online": online, "blocked": blocked,
        "open_alerts": open_alerts, "white": white, "black": black,
        "bytes_in": traffic[0] or 0, "bytes_out": traffic[1] or 0,
    }


@router.get("/traffic/{device_id}")
def device_traffic(device_id: int, limit: int = 24, db: Session = Depends(get_session)):
    rows = db.query(DeviceTraffic).filter(
        DeviceTraffic.device_id == device_id
    ).order_by(DeviceTraffic.id.desc()).limit(limit).all()
    return [r.__dict__ for r in rows]
