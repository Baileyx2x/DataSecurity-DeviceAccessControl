"""网络工具 — 自动识别本机 LAN 网段与默认网卡(跨 Linux / Windows)。"""

import ipaddress
import socket
import sys

import psutil


def detect_interface() -> str:
    """选择第一个具备有效 IPv4 的物理网卡。

    返回空字符串表示交给 Scapy 自动按路由选路(Windows 上 psutil 的
    连接名与 Scapy 的接口名不是同一套体系,不宜硬塞给 srp(iface=...))。
    """
    for name, addrs in psutil.net_if_addrs().items():
        low = name.lower()
        if sys.platform == "win32":
            # Windows: 跳过回环 / 隧道 / 虚拟伪接口
            if "loopback" in low or "isatap" in low or "teredo" in low:
                continue
        else:
            # Linux: 跳过 lo / docker / 网桥 / veth
            if name == "lo" or low.startswith(("docker", "br-", "veth")):
                continue
        for a in addrs:
            if a.family == socket.AF_INET and not a.address.startswith("169.254"):
                return name
    return ""  # 留空 = 由 Scapy 自动选路,不再硬编码 eth0


def detect_lan_cidr() -> str:
    """根据 detect_interface() 选中的网卡推算 CIDR;选不到则退回首个有效 IPv4。"""
    addr_map = psutil.net_if_addrs()
    iface = detect_interface()
    candidates = [addr_map[iface]] if iface and iface in addr_map else addr_map.values()
    for addrs in candidates:
        for a in addrs:
            if a.family == socket.AF_INET and not a.address.startswith(("127.", "169.254")):
                net = ipaddress.IPv4Network(f"{a.address}/{a.netmask}", strict=False)
                return str(net)
    return "192.168.1.0/24"
