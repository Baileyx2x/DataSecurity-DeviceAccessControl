"""设备指纹模块 — OUI 厂商 / mDNS 主机名 / NetBIOS / OS 推测。"""

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
