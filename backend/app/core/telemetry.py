"""状态采集 — 维护设备在线/离线状态,写入 access_log,广播 WebSocket 事件,流量采样,被动 ARP 监听。"""

import ipaddress
import json
import threading
from collections import Counter
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..models.base import SessionLocal
from ..models.device import Device
from ..models.access_log import AccessLog
from ..models.traffic import DeviceTraffic
from ..ws.manager import manager
from ..ws.events import device_online, device_offline
from ..utils.logger import logger


OFFLINE_THRESHOLD_SEC = 120

_passive_sniffer: object | None = None  # AsyncSniffer | None


def mark_online(db: Session, device_id: int, ip: str) -> None:
    db.add(AccessLog(device_id=device_id, event_type="online", ip=ip))
    db.commit()

    dev = db.get(Device, device_id)
    if dev:
        manager.broadcast_sync(device_online(dev))


def reap_offline(db: Session) -> int:
    cutoff = datetime.now() - timedelta(seconds=OFFLINE_THRESHOLD_SEC)
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
    from scapy.all import IP, TCP, UDP, sniff

    # 预计算网段前缀,避免每包重复解析
    net = ipaddress.IPv4Network(cidr, strict=False) if cidr else None

    stats: dict[str, dict] = {}  # ip → {pkt_in, pkt_out, bytes_in, bytes_out, ports, dst_ips}

    def _count(pkt):
        if not pkt.haslayer(IP):
            return
        ip = pkt[IP]
        src = ip.src
        dst = ip.dst
        length = len(pkt)

        # 提取 L4 端口
        dport = None
        if pkt.haslayer(TCP):
            dport = pkt[TCP].dport
        elif pkt.haslayer(UDP):
            dport = pkt[UDP].dport

        inbound = net is not None and ipaddress.IPv4Address(dst) in net
        entry = stats.setdefault(src, {
            "pkt_in": 0, "pkt_out": 0,
            "bytes_in": 0, "bytes_out": 0,
            "ports": [], "dst_ips": set(),
        })
        if inbound:
            entry["pkt_in"] += 1
            entry["bytes_in"] += length
            if dport:
                entry["ports"].append(dport)
        else:
            entry["pkt_out"] += 1
            entry["bytes_out"] += length
            if dport:
                entry["ports"].append(dport)
            entry["dst_ips"].add(dst)

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
            unique_dst_ips=len(s["dst_ips"]),
            unique_dst_ports=len(set(s["ports"])),
        ))
    db.commit()
    logger.info(f"[telemetry] traffic sampled: {len(stats)} IPs in {duration}s")


# ===================================================================
#  被动 ARP 监听 — 设备一连网发 ARP 包即标记上线,无需等定时扫描
# ===================================================================

def start_passive_arp(iface: str = "") -> None:
    """启动后台 ARP 嗅探,检测设备上线(实时,不受扫描间隔限制)。"""
    global _passive_sniffer
    if _passive_sniffer is not None:
        return

    from scapy.all import ARP, AsyncSniffer

    def _on_arp(pkt):
        if not pkt.haslayer(ARP):
            return
        arp = pkt[ARP]
        src_mac = arp.hwsrc.lower() if arp.hwsrc else None
        src_ip = arp.psrc
        if not src_mac or src_ip == "0.0.0.0":
            return

        db = SessionLocal()
        try:
            dev = db.query(Device).filter(Device.mac == src_mac).first()
            if dev is None:
                return
            if dev.status == "online" and dev.ip == src_ip:
                return  # 无变化,跳过
            dev.status = "online"
            dev.last_seen = datetime.now()
            dev.ip = src_ip
            db.add(AccessLog(device_id=dev.id, event_type="online", ip=src_ip))
            db.commit()
            manager.broadcast_sync(device_online(dev))
            logger.info(f"[telemetry] passive ARP: {src_ip} ({src_mac}) online")
        except Exception:
            db.rollback()
        finally:
            db.close()

    logger.info(f"[telemetry] starting passive ARP listener{iface and ' on ' + iface}")
    kwargs = {"prn": _on_arp, "filter": "arp", "store": False}
    if iface:
        kwargs["iface"] = iface
    _passive_sniffer = AsyncSniffer(**kwargs)
    _passive_sniffer.start()


def stop_passive_arp() -> None:
    global _passive_sniffer
    if _passive_sniffer is not None:
        _passive_sniffer.stop()
        _passive_sniffer = None
        logger.info("[telemetry] passive ARP listener stopped")
