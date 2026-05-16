"""设备指纹模块 — OUI 厂商 / 主机名 / OS 推测。"""

from dataclasses import dataclass
from ..utils.oui import lookup_vendor


@dataclass
class Fingerprint:
    vendor: str | None = None
    hostname: str | None = None
    os_guess: str | None = None


def fingerprint_device(ip: str, mac: str) -> Fingerprint:
    """整合 OUI / mDNS / NetBIOS 等手段,返回设备画像。"""
    fp = Fingerprint()
    fp.vendor = lookup_vendor(mac)
    # TODO: mDNS / NetBIOS 主机名解析
    # TODO: 被动 OS 指纹 (TTL / TCP 窗口)
    return fp
