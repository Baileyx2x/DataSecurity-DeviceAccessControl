"""设备发现 — ARP 扫描 + ICMP 探测。

依赖 Scapy:
  - Linux: 需 root / CAP_NET_RAW
  - Windows: 需安装 Npcap (安装时勾选 "WinPcap API-compatible Mode"),并以管理员运行
"""

from dataclasses import dataclass
from typing import List

from ..config import settings
from ..utils.logger import logger
from ..utils.net import detect_lan_cidr, detect_interface


@dataclass
class DiscoveredHost:
    ip: str
    mac: str


def arp_scan(cidr: str | None = None, iface: str | None = None, timeout: int = 2) -> List[DiscoveredHost]:
    """对指定网段执行 ARP 广播扫描,返回 (IP, MAC) 列表。"""
    from scapy.all import ARP, Ether, srp  # 延迟导入,便于在无 scapy 环境下做单测 mock

    cidr = cidr or settings.lan_cidr or detect_lan_cidr()
    iface = iface or settings.lan_interface or detect_interface()
    logger.info(f"[discovery] ARP scan: iface={iface} cidr={cidr}")

    pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=cidr)
    # iface 为空时不传该参数,让 Scapy 按路由自动选路
    # (Windows 上 psutil 连接名 != Scapy 接口名,强行传入会报错)
    kwargs = {"timeout": timeout, "verbose": 0}
    if iface:
        kwargs["iface"] = iface
    answered, _ = srp(pkt, **kwargs)
    hosts = [DiscoveredHost(ip=r.psrc, mac=r.hwsrc.lower()) for _, r in answered]
    logger.info(f"[discovery] found {len(hosts)} hosts")
    return hosts


def nmap_scan(cidr: str | None = None) -> List[DiscoveredHost]:
    """用 Nmap 做主机发现 (-sn ARP/Ping 扫描),返回 (IP, MAC) 列表。

    不依赖 Npcap/Scapy,适合 Windows 上未装 Npcap 时的后备发现方案。
    前提:本机已安装 Nmap 且 nmap 可执行文件在 PATH 中
    (Windows 安装 Nmap 时其自带 Npcap;以管理员运行才能拿到 MAC)。
    """
    import nmap  # python-nmap;延迟导入,便于无 nmap 环境单测 mock

    cidr = cidr or settings.lan_cidr or detect_lan_cidr()
    logger.info(f"[discovery] nmap scan: cidr={cidr}")

    nm = nmap.PortScanner()
    nm.scan(hosts=cidr, arguments="-sn -n")  # -sn 只发现不扫端口, -n 不做 DNS
    hosts: List[DiscoveredHost] = []
    for ip in nm.all_hosts():
        if nm[ip].state() != "up":
            continue
        # MAC 仅在同网段且有权限时可得,否则置空
        mac = nm[ip]["addresses"].get("mac", "").lower()
        hosts.append(DiscoveredHost(ip=ip, mac=mac))
    logger.info(f"[discovery] nmap found {len(hosts)} hosts")
    return hosts


def discover(cidr: str | None = None) -> List[DiscoveredHost]:
    """统一发现入口:优先 ARP(Scapy),失败则回退 Nmap。"""
    try:
        hosts = arp_scan(cidr)
        if hosts:
            return hosts
        logger.warning("[discovery] ARP scan empty, falling back to nmap")
    except Exception as e:
        logger.warning(f"[discovery] ARP scan failed ({e}), falling back to nmap")
    try:
        return nmap_scan(cidr)
    except Exception as e:
        logger.error(f"[discovery] nmap scan failed: {e}")
        return []


def icmp_probe(ip: str, timeout: int = 1) -> bool:
    """对单个 IP 发送 ICMP Echo,返回是否存活。"""
    from scapy.all import IP, ICMP, sr1
    pkt = IP(dst=ip) / ICMP()
    resp = sr1(pkt, timeout=timeout, verbose=0)
    return resp is not None
