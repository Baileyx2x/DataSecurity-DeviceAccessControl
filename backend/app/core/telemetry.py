"""状态采集 — 维护设备在线/离线状态,写入 access_log,广播 WebSocket 事件,流量采样,被动监听(ARP/DHCP/TCP SYN 指纹)。"""

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
#  被动监听 — ARP 上线检测 + DHCP 指纹 + TCP SYN 指纹
#  设备一连网即可识别上线状态和操作系统,无需等定时扫描
# ===================================================================
# BPF: ARP 广播 / DHCP 客户端请求 / TCP SYN (不含 SYN-ACK)
_PASSIVE_FILTER = (
    "arp"
    " or (udp and src port 68 and dst port 67)"
    " or (tcp[tcpflags] & (tcp-syn) != 0 and tcp[tcpflags] & (tcp-ack) == 0)"
)

def start_passive_arp(iface: str = "") -> None:
    """启动后台被动监听 (ARP + DHCP + TCP SYN),实时检测设备上线并采集指纹。"""
    global _passive_sniffer
    if _passive_sniffer is not None:
        return

    from scapy.all import ARP, DHCP, BOOTP, TCP, AsyncSniffer
    from . import fingerprint as fp

    def _on_packet(pkt):

        # ── 1) ARP ──
        if pkt.haslayer(ARP):
            arp = pkt[ARP]
            src_mac = (arp.hwsrc or "").lower()
            src_ip = arp.psrc
            if not src_mac or src_ip == "0.0.0.0":
                return
            db = SessionLocal()
            try:
                dev = db.query(Device).filter(Device.mac == src_mac).first()
                if dev is None:
                    return
                if dev.status == "online" and dev.ip == src_ip:
                    return
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
            return

        # ── 2) DHCP 指纹 ──
        if pkt.haslayer(BOOTP) and pkt.haslayer(DHCP):
            src_mac = (pkt.src or "").lower() if hasattr(pkt, "src") else None
            if not src_mac:
                return
            dhcp_os, dhcp_host = fp.fingerprint_dhcp(pkt)
            if not dhcp_os and not dhcp_host:
                return
            db = SessionLocal()
            try:
                dev = db.query(Device).filter(Device.mac == src_mac).first()
                if dev is None:
                    return
                changed = False
                # 仅在当前无 OS 猜测或 DHCP 提供更好的信息时更新
                if dhcp_os and (not dev.os_guess or not _is_tcp_syn_os(dev.os_guess)):
                    dev.os_guess = dhcp_os
                    changed = True
                if dhcp_host and not dev.hostname:
                    dev.hostname = dhcp_host
                    changed = True
                if changed:
                    db.commit()
                    logger.info(
                        f"[telemetry] DHCP fingerprint: {dev.ip} ({src_mac})"
                        f" → OS={dhcp_os} hostname={dhcp_host}"
                    )
            except Exception:
                db.rollback()
            finally:
                db.close()
            return

        # ── 3) TCP SYN 指纹 ──
        if pkt.haslayer(TCP):
            tcp_flags = pkt[TCP].flags
            # 仅处理纯 SYN (SYN=1, ACK=0)
            if not (tcp_flags & 0x02) or (tcp_flags & 0x10):
                return
            src_mac = (pkt.src or "").lower() if hasattr(pkt, "src") else None
            if not src_mac:
                return
            syn_os = fp.fingerprint_tcp_syn(pkt)
            if not syn_os:
                return
            db = SessionLocal()
            try:
                dev = db.query(Device).filter(Device.mac == src_mac).first()
                if dev is None:
                    return
                # TCP SYN 指纹优先级最高,覆盖已有猜测
                if dev.os_guess != syn_os:
                    dev.os_guess = syn_os
                    db.commit()
                    logger.info(
                        f"[telemetry] TCP SYN fingerprint: {dev.ip} ({src_mac})"
                        f" → {syn_os}"
                    )
            except Exception:
                db.rollback()
            finally:
                db.close()

    logger.info(f"[telemetry] starting passive monitor (ARP+DHCP+TCP){' on ' + iface if iface else ''}")
    kwargs = {"prn": _on_packet, "filter": _PASSIVE_FILTER, "store": False}
    if iface:
        kwargs["iface"] = iface
    _passive_sniffer = AsyncSniffer(**kwargs)
    _passive_sniffer.start()


def _is_tcp_syn_os(os_str: str | None) -> bool:
    """判断现有 OS 猜测是否来自 TCP SYN 指纹(高置信度,不应被 DHCP 覆盖)。"""
    if not os_str:
        return False
    syn_keywords = ("Windows 10", "Windows 11", "Windows 7", "Windows 8",
                    "macOS", "iOS", "Android", "Linux (modern)", "Cisco")
    return any(kw in os_str for kw in syn_keywords)


def stop_passive_arp() -> None:
    global _passive_sniffer
    if _passive_sniffer is not None:
        _passive_sniffer.stop()
        _passive_sniffer = None
        logger.info("[telemetry] passive monitor stopped")
