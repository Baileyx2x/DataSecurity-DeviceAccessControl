"""状态采集 — 维护设备在线/离线状态,写入 access_log,广播 WebSocket 事件。"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..models.device import Device
from ..models.access_log import AccessLog
from ..ws.manager import manager
from ..ws.events import device_online, device_offline


OFFLINE_THRESHOLD_SEC = 120


def mark_online(db: Session, device_id: int, ip: str) -> None:
    db.add(AccessLog(device_id=device_id, event_type="online", ip=ip))
    db.commit()

    dev = db.get(Device, device_id)
    if dev:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(manager.broadcast(device_online(dev)))
        except Exception:
            pass


def reap_offline(db: Session) -> int:
    cutoff = datetime.utcnow() - timedelta(seconds=OFFLINE_THRESHOLD_SEC)
    gone: list[Device] = []
    for dev in db.query(Device).filter(Device.status == "online", Device.last_seen < cutoff).all():
        dev.status = "offline"
        db.add(AccessLog(device_id=dev.id, event_type="offline", ip=dev.ip))
        gone.append(dev)
    db.commit()

    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            for dev in gone:
                loop.create_task(manager.broadcast(device_offline(dev)))
    except Exception:
        pass

    return len(gone)
