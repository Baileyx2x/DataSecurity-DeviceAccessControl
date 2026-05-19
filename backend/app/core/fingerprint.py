"""设备指纹模块 — OUI 厂商 / mDNS 主机名 / NetBIOS / OS 推测 / TCP SYN 被动指纹 / DHCP 指纹。"""

import socket
import subprocess
import sys
from dataclasses import dataclass
from ..utils.oui import lookup_vendor
from ..utils.logger import logger


@dataclass
class Fingerprint:
    vendor: str | None = None
    hostname: str | None = None
    os_guess: str | None = None


def fingerprint_device(ip: str, mac: str) -> Fingerprint:
    fp = Fingerprint()
    fp.vendor = lookup_vendor(mac)
    fp.hostname = _resolve_hostname(ip)
    fp.os_guess = _guess_os(ip, mac)
    return fp


# ===== 主机名解析 =====

def _resolve_hostname(ip: str) -> str | None:
    """依次尝试 DNS PTR / mDNS / NetBIOS 解析主机名。"""
    # 1) DNS 反向解析
    name = _dns_reverse(ip)
    if name:
        return name
    # 2) NetBIOS (Windows 专属)
    name = _netbios_name(ip)
    if name:
        return name
    # 3) mDNS (仅 Linux/macOS 硬件支持,Windows 需额外工具)
    name = _mdns_name(ip)
    if name:
        return name
    return None


def _dns_reverse(ip: str) -> str | None:
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host if host and host != ip else None
    except Exception:
        return None


def _netbios_name(ip: str) -> str | None:
    """通过 nmblookup 查询 NetBIOS 名;Windows 上可通过 nbtstat 实现。"""
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                ["nbtstat", "-A", ip],
                timeout=5, text=True, stderr=subprocess.DEVNULL,
            )
            for line in out.splitlines():
                if "<00>" in line and "UNIQUE" in line:
                    name = line.strip().split(None, 1)[0]
                    if name and name != ip:
                        return name
        except Exception:
            pass
    else:
        try:
            out = subprocess.check_output(
                ["nmblookup", "-A", ip],
                timeout=5, text=True, stderr=subprocess.DEVNULL,
            )
            for line in out.splitlines():
                if "<00>" in line:
                    parts = line.strip().split()
                    if parts:
                        name = parts[0]
                        if name and name != ip:
                            return name
        except Exception:
            pass
    return None


def _mdns_name(ip: str) -> str | None:
    """通过 avahi-resolve / dns-sd 做 mDNS 反查。"""
    if sys.platform == "win32":
        # Windows 上 mDNS 反查少见,跳过
        return None
    try:
        out = subprocess.check_output(
            ["avahi-resolve-address", ip],
            timeout=3, text=True, stderr=subprocess.DEVNULL,
        )
        if out.strip():
            return out.strip().split()[-1].rstrip(".")
    except Exception:
        pass
    return None


# ===== OS 推测 =====

def _guess_os(ip: str, mac: str | None) -> str | None:
    """通过 TTL(需主动探测) + OUI 厂商 + 主机名关键词 推测 OS。

    被动 TCP 窗口指纹过于复杂,这里用快速启发式:
    - OUI 为 Apple 厂商 → iOS/macOS
    - 主机名含 "iPhone"/"iPad"/"MacBook"/"android" 等
    - ping TTL: Windows 128, Linux 64, macOS/iOS 64, 安卓 64
    """
    hints: list[str] = []

    # 1) OUI 启发
    vendor = (lookup_vendor(mac) if mac else None) or ""
    vendor_low = vendor.lower()
    if "apple" in vendor_low:
        hints.append("likely Apple(iOS/macOS)")
    elif "samsung" in vendor_low or "xiaomi" in vendor_low or "huawei" in vendor_low or "oneplus" in vendor_low or "oppo" in vendor_low or "vivo" in vendor_low:
        hints.append("likely Android")

    # 2) TTL 启发 (轻量 ping)
    ttl = _ping_ttl(ip)
    if ttl:
        if ttl >= 120:
            hints.append(f"TTL={ttl}→likely Windows")
        elif 60 <= ttl <= 64:
            pass  # 太常见,不加判断
        elif ttl < 60:
            hints.append(f"TTL={ttl}→maybe embedded/IoT")

    if hints:
        return " | ".join(hints)
    return None


def _ping_ttl(ip: str) -> int | None:
    """对目标发一个 ICMP Echo,抓取 TTL 值。"""
    param = "-n 1 -w 1" if sys.platform == "win32" else "-c 1 -W 1"
    try:
        out = subprocess.check_output(
            f"ping {param} {ip}",
            shell=True, timeout=3, text=True, stderr=subprocess.DEVNULL,
        )
        for line in out.splitlines():
            low = line.lower()
            if "ttl=" in low:
                ttl_str = low.split("ttl=")[1].split()[0].split("<")[0]
                try:
                    return int(ttl_str)
                except ValueError:
                    pass
    except Exception:
        pass
    return None


# ===================================================================
#  TCP SYN 被动指纹 (p0f 风格)
# ===================================================================

from collections import namedtuple

SynSig = namedtuple("SynSig", ["ttl_lo", "ttl_hi", "win_lo", "win_hi", "options", "os_label"])

TCP_SYN_SIGS: list[SynSig] = [
    # ── Windows ──
    SynSig(120, 130, 64000, 66000, "MSS,NOP,WS,NOP,NOP,SACK", "Windows 10/11"),
    SynSig(120, 130, 64000, 66000, "MSS,WS,NOP,NOP,SACK", "Windows 10/11 (variant)"),
    SynSig(120, 130, 16000, 17000, "MSS,NOP,WS,NOP,NOP,SACK", "Windows Vista/7"),
    SynSig(120, 130,  8100,  8300, "MSS,NOP,WS,NOP,NOP,SACK", "Windows 7/8"),
    SynSig(120, 130, 32000, 33000, "MSS,NOP,WS,NOP,NOP,SACK", "Windows Server"),
    # ── Linux ──
    SynSig( 52,  66, 28000, 30000, "MSS,SACK,TS,WS", "Linux (modern)"),
    SynSig( 52,  66, 28000, 30000, "MSS,SACK,TS,WS,NOP,NOP", "Linux"),
    SynSig( 52,  66, 57000, 59000, "MSS,SACK,TS,WS", "Linux (ARM/IoT)"),
    SynSig( 52,  66, 14000, 14500, "MSS,SACK,TS,WS", "Linux (older)"),
    # ── macOS / iOS ──
    SynSig( 52,  66, 64000, 66000, "MSS,NOP,WS,NOP,NOP,TS,NOP,NOP,SACK", "macOS/iOS"),
    SynSig( 52,  66, 64000, 66000, "MSS,SACK,TS,WS", "macOS/iOS (newer)"),
    SynSig( 52,  66, 64000, 66000, "MSS,WS,NOP,NOP,TS,NOP,NOP,SACK", "iOS 14+"),
    # ── Android ──
    SynSig( 52,  66, 64000, 66000, "MSS,NOP,WS,NOP,NOP,SACK,NOP,NOP,TS", "Android"),
    SynSig( 52,  66, 58000, 59000, "MSS,SACK,TS,WS", "Android/Linux"),
    SynSig( 52,  66, 64000, 66000, "MSS,SACK,TS,WS,NOP,NOP", "Android (kernel 5.x)"),
    # ── 网络设备 / IoT ──
    SynSig(240, 260, 1400, 1500, "MSS,NOP,NOP,SACK", "Cisco IOS"),
    SynSig(240, 260, 3800, 3900, "MSS,NOP,NOP,SACK", "Cisco VPN"),
    SynSig( 50,  66, 1400, 1500, "MSS,NOP,NOP,SACK", "Embedded/IoT (BusyBox)"),
    SynSig( 60,  70, 2048, 2100, "MSS", "IP Camera / IoT (minimal)"),
]

_TCP_SYN_LABELS: set[str] = {s.os_label for s in TCP_SYN_SIGS}

OPT_KIND_NAME = {0: None, 1: "NOP", 2: "MSS", 3: "WS", 4: "SACK", 5: "SACK", 8: "TS"}


def is_tcp_syn_os_label(label: str | None) -> bool:
    """判断 os_guess 是否来自 TCP SYN 指纹(高置信度)。"""
    return bool(label and label in _TCP_SYN_LABELS)


def _parse_tcp_options(pkt) -> str | None:
    try:
        from scapy.all import TCP
        tcp = pkt[TCP]
        names = []
        for o in tcp.options:
            kind = o[0]
            if kind == 0:
                break
            name = OPT_KIND_NAME.get(kind)
            if name:
                names.append(name)
        return ",".join(names) if names else None
    except Exception:
        return None


def fingerprint_tcp_syn(pkt) -> str | None:
    try:
        from scapy.all import IP, TCP
        ip = pkt[IP]; tcp = pkt[TCP]
        ttl = ip.ttl; win = tcp.window
    except Exception:
        return None

    opts = _parse_tcp_options(pkt)
    if not opts:
        return None

    for sig in TCP_SYN_SIGS:
        if (sig.ttl_lo <= ttl <= sig.ttl_hi and sig.win_lo <= win <= sig.win_hi
                and opts == sig.options):
            return sig.os_label
    return None


# ===================================================================
#  DHCP 指纹 (Option 60 Vendor Class / Option 12 Hostname)
# ===================================================================

DHCP_VENDOR_MAP = {
    "MSFT 5.0": "Windows 10/11",
    "MSFT": "Windows",
    "android-dhcp": "Android",
    "dhcpcd": "Android/Linux",
    "udhcp": "Embedded Linux (IoT)",
    "dnsmasq": "Linux/OpenWrt",
    "dnsmasq-dhcp": "Linux (dnsmasq)",
    "ISC DHCP": "Linux/BSD",
}


def _dhcp_decode(val) -> str:
    """安全解码 DHCP option 值 (bytes → str)。"""
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return str(val or "")


def fingerprint_dhcp(pkt) -> tuple[str | None, str | None]:
    """解析 DHCP 请求包,返回 (os_guess, hostname)。"""
    from scapy.all import DHCP, BOOTP
    if not pkt.haslayer(BOOTP) or not pkt.haslayer(DHCP):
        return None, None

    os_guess: str | None = None
    hostname: str | None = None

    for opt in pkt[DHCP].options:
        if opt == "end":
            break
        if not isinstance(opt, tuple) or len(opt) < 2:
            continue
        key, *vals = opt
        if key == "vendor_class_id" and vals:
            vstr = _dhcp_decode(vals[0])
            if not vstr:
                continue
            for pattern, os_name in DHCP_VENDOR_MAP.items():
                if vstr.lower().startswith(pattern.lower()):
                    os_guess = os_name
                    break
            if not os_guess:
                os_guess = vstr[:64]
        elif key == "hostname" and vals:
            h = _dhcp_decode(vals[0])
            if h:
                hostname = h[:255]

    return os_guess, hostname
