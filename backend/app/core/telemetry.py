"""状态采集 — 维护设备在线/离线状态,写入 access_log,广播 WebSocket 事件,流量采样。"""

import ipaddress
import json
from collections import Counter
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..models.device import Device
from ..models.access_log import AccessLog
from ..models.traffic import DeviceTraffic
from ..ws.manager import manager
from ..ws.events import device_online, device_offline
from ..utils.logger import logger


OFFLINE_THRESHOLD_SEC = 120


def mark_online(db: Session, device_id: int, ip: str) -> None:
    db.add(AccessLog(device_id=device_id, event_type="online", ip=ip))
    db.commit()

    dev = db.get(Device, device_id)
    if dev:
        manager.broadcast_sync(device_online(dev))


def reap_offline(db: Session) -> int:
    cutoff = datetime.utcnow() - timedelta(seconds=OFFLINE_THRESHOLD_SEC)
    gone: list[Device] = []
    for dev in db.query(Device).filter(Device.status == "online", Device.last_seen < cutoff).all():
        dev.status = "offline"
        db.add(AccessLog(device_id=dev.id, event_type="offline", ip=dev.ip))
        gone.append(dev)
    db.commit()

    for dev in gone:
        manager.broadcast_sync(device_offline(dev))

    return len(gone)


def sample_traffic(db: Session, cidr: str, iface: str, duration: int = 5):
    """对网段进行 {duration}s 轻量抓包,按源 IP 统计流量写入 device_traffic 表。

    只抓 IP 层包头,不触碰载荷,避免隐私风险。
    """
    from scapy.all import IP, sniff

    # 预计算网段前缀,避免每包重复解析
    net = ipaddress.IPv4Network(cidr, strict=False) if cidr else None

    stats: dict[str, dict] = {}  # ip → {pkt_in, pkt_out, bytes_in, bytes_out, ports}

    def _count(pkt):
        if not pkt.haslayer(IP):
            return
        ip = pkt[IP]
        src = ip.src
        dst = ip.dst
        length = len(pkt)

        inbound = net is not None and ipaddress.IPv4Address(dst) in net
        entry = stats.setdefault(src, {"pkt_in": 0, "pkt_out": 0, "bytes_in": 0, "bytes_out": 0, "ports": []})
        if inbound:
            entry["pkt_in"] += 1
            entry["bytes_in"] += length
        else:
            entry["pkt_out"] += 1
            entry["bytes_out"] += length

    try:
        sniff(iface=iface, timeout=duration, prn=_count, store=False, filter="ip")
    except Exception as e:
        logger.warning(f"[telemetry] traffic sample error: {e}")
        return

    if not stats:
        return

    # 一次 IN 查询拿到所有匹配的设备
    ips = list(stats.keys())
    devices = {d.ip: d for d in db.query(Device).filter(Device.ip.in_(ips)).all()}

    for ip, s in stats.items():
        dev = devices.get(ip)
        if not dev:
            continue
        top = json.dumps([p for p, _ in Counter(s["ports"]).most_common(5)])
        db.add(DeviceTraffic(
            device_id=dev.id,
            pkt_in=s["pkt_in"], pkt_out=s["pkt_out"],
            bytes_in=s["bytes_in"], bytes_out=s["bytes_out"],
            top_ports=top,
        ))
    db.commit()
    logger.info(f"[telemetry] traffic sampled: {len(stats)} IPs in {duration}s")
