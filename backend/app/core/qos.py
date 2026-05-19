"""QoS 带宽限速 — 基于 Linux tc (HTB) 按设备 IP 限制上下行速率。
仅支持 Linux。Windows / macOS 上会返回明确错误。
"""

import shutil
import subprocess
import sys
from sqlalchemy.orm import Session
from ..models.device import Device
from ..utils.logger import logger


_active: dict[int, dict] = {}  # device_id → {down_kbps, up_kbps}
_tc_ok: bool | None = None      # 缓存 tc 可用性检查
_root_ok: set[str] = set()      # 缓存已建立 HTB 根队列的接口名
_ingress_ok: set[str] = set()   # 缓存已建立 ingress qdisc 的接口名


class QosError(RuntimeError):
    """QoS 操作失败 (平台不支持/tc 命令缺失/权限不足等)。"""
    pass


def _check_platform() -> None:
    global _tc_ok
    if _tc_ok is not None:
        return
    if sys.platform != "linux":
        raise QosError("QoS 带宽限速仅支持 Linux 系统 (需要 tc 命令)")
    if shutil.which("tc") is None:
        raise QosError("未找到 tc 命令,请安装 iproute2")
    _tc_ok = True


def _run(*args: str) -> str:
    """执行 tc 命令,失败时抛出 QosError。"""
    try:
        r = subprocess.run(list(args), capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        raise QosError(f"tc 命令不可用: {' '.join(args)}")
    except Exception as e:
        raise QosError(f"tc 执行异常: {e}")
    if r.returncode != 0:
        err = r.stderr.strip()
        raise QosError(err if err else f"tc 返回 {r.returncode}")
    return r.stdout


def _ensure_root(iface: str) -> None:
    if iface in _root_ok:
        return
    out = _run("tc", "qdisc", "show", "dev", iface)
    if "htb" not in out:
        _run("tc", "qdisc", "add", "dev", iface, "root", "handle", "1:", "htb", "default", "30")
        _run("tc", "class", "add", "dev", iface, "parent", "1:", "classid", "1:30", "htb", "rate", "1000mbit")
        logger.info(f"[qos] created root HTB qdisc on {iface}")
    _root_ok.add(iface)


def _class_id(device_id: int) -> str:
    return f"1:{min(device_id, 9999)}0"


def _filter_prio(device_id: int) -> str:
    """每个 device 唯一的 filter priority,方便精确删除。"""
    return str((device_id % 65535) + 1)


def _ensure_ingress(iface: str) -> None:
    """确保接口上有 ingress qdisc (每接口仅一个,所有设备共享)。"""
    if iface in _ingress_ok:
        return
    out = _run("tc", "qdisc", "show", "dev", iface)
    if "ingress" not in out:
        _run("tc", "qdisc", "add", "dev", iface, "handle", "ffff:", "ingress")
        logger.info(f"[qos] created ingress qdisc on {iface}")
    _ingress_ok.add(iface)


def limit_device(db: Session, device: Device, iface: str,
                 down_kbps: int = 0, up_kbps: int = 0) -> None:
    """对设备应用带宽限制。仅 Linux 有效,其他平台抛出 QosError。"""
    _check_platform()

    if device.id in _active:
        _remove_tc(device, iface)

    _ensure_root(iface)
    cid = _class_id(device.id)
    prio = _filter_prio(device.id)
    ip = device.ip

    if down_kbps > 0:
        burst = max(down_kbps, 1600)
        _run("tc", "class", "add", "dev", iface, "parent", "1:",
             "classid", cid, "htb",
             "rate", f"{down_kbps}kbit",
             "ceil", f"{down_kbps}kbit",
             "burst", str(burst))
        _run("tc", "filter", "add", "dev", iface, "protocol", "ip",
             "parent", "1:", "prio", prio, "u32",
             "match", "ip", "dst", ip,
             "flowid", cid)

    if up_kbps > 0:
        _ensure_ingress(iface)
        burst_k = max(up_kbps // 8, 10)
        _run("tc", "filter", "add", "dev", iface, "parent", "ffff:",
             "protocol", "ip", "prio", prio, "u32",
             "match", "ip", "src", ip,
             "police", "rate", f"{up_kbps}kbit",
             "burst", f"{burst_k}k",
             "drop", "flowid", "ffff:")

    _active[device.id] = {"down_kbps": down_kbps, "up_kbps": up_kbps}
    device.qos_down_kbps = down_kbps or None
    device.qos_up_kbps = up_kbps or None
    db.commit()
    logger.info(f"[qos] limited device {ip}: down={down_kbps}kbps up={up_kbps}kbps")


def remove_limit(db: Session, device: Device, iface: str) -> None:
    """移除设备的带宽限制。"""
    _check_platform()
    _remove_tc(device, iface)
    _active.pop(device.id, None)
    device.qos_down_kbps = None
    device.qos_up_kbps = None
    db.commit()
    logger.info(f"[qos] removed limit for {device.ip}")


def _remove_tc(device: Device, iface: str) -> None:
    """移除设备的 tc 规则。不存在的规则静默忽略。"""
    cid = _class_id(device.id)
    prio = _filter_prio(device.id)
    ip = device.ip
    info = _active.get(device.id, {})

    if info.get("down_kbps", 0) > 0:
        try:
            _run("tc", "filter", "del", "dev", iface, "parent", "1:",
                 "prio", prio, "u32",
                 "match", "ip", "dst", ip, "flowid", cid)
        except QosError:
            pass
        try:
            _run("tc", "class", "del", "dev", iface, "classid", cid)
        except QosError:
            pass

    if info.get("up_kbps", 0) > 0:
        try:
            _run("tc", "filter", "del", "dev", iface, "parent", "ffff:",
                 "prio", prio, "u32",
                 "match", "ip", "src", ip)
        except QosError:
            pass


def get_active() -> dict[int, dict]:
    return dict(_active)


def restore_limits(db: Session, iface: str) -> None:
    """启动时恢复 DB 中已记录的限速 (仅 Linux)。"""
    if sys.platform != "linux":
        return
    devices = db.query(Device).filter(
        (Device.qos_down_kbps.isnot(None)) | (Device.qos_up_kbps.isnot(None))
    ).all()
    for dev in devices:
        if dev.id in _active:
            continue
        try:
            limit_device(db, dev, iface,
                        down_kbps=dev.qos_down_kbps or 0,
                        up_kbps=dev.qos_up_kbps or 0)
        except QosError:
            logger.warning(f"[qos] failed to restore limit for {dev.ip}")
