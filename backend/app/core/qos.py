"""QoS 带宽限速 — 基于 Linux tc (HTB) 按设备 IP 限制上下行速率。
仅支持 Linux。Windows / macOS 上会返回明确错误。
"""

import subprocess
import sys
from sqlalchemy.orm import Session
from ..models.device import Device
from ..utils.logger import logger


_active: dict[int, dict] = {}  # device_id → {down_kbps, up_kbps}


class QosError(RuntimeError):
    """QoS 操作失败 (平台不支持/tc 命令缺失/权限不足等)。"""
    pass


def _check_platform() -> None:
    """确保当前平台支持 tc,否则直接报错。"""
    if sys.platform != "linux":
        raise QosError("QoS 带宽限速仅支持 Linux 系统 (需要 tc 命令)")
    if subprocess.run(["which", "tc"], capture_output=True).returncode != 0:
        raise QosError("未找到 tc 命令,请安装 iproute2")


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
        if err and "RTNETLINK" not in err:
            raise QosError(err or f"tc 返回 {r.returncode}")
    return r.stdout


def _ensure_root(iface: str) -> None:
    """确保接口上有 HTB 根队列。"""
    out = _run("tc", "qdisc", "show", "dev", iface)
    if "htb" not in out:
        _run("tc", "qdisc", "add", "dev", iface, "root", "handle", "1:", "htb", "default", "30")
        _run("tc", "class", "add", "dev", iface, "parent", "1:", "classid", "1:30", "htb", "rate", "1000mbit")
        logger.info(f"[qos] created root HTB qdisc on {iface}")


def _class_id(device_id: int) -> str:
    return f"1:{min(device_id, 9999)}0"


def limit_device(db: Session, device: Device, iface: str,
                 down_kbps: int = 0, up_kbps: int = 0) -> None:
    """对设备应用带宽限制。仅 Linux 有效,其他平台抛出 QosError。"""
    _check_platform()

    if device.id in _active:
        _remove_tc(device, iface)

    _ensure_root(iface)
    cid = _class_id(device.id)
    ip = device.ip

    if down_kbps > 0:
        burst = max(down_kbps, 1600)
        _run("tc", "class", "add", "dev", iface, "parent", "1:",
             "classid", cid, "htb",
             "rate", f"{down_kbps}kbit",
             "ceil", f"{down_kbps}kbit",
             "burst", str(burst))
        _run("tc", "filter", "add", "dev", iface, "protocol", "ip",
             "parent", "1:", "prio", "1", "u32",
             "match", "ip", "dst", ip,
             "flowid", cid)

    if up_kbps > 0:
        handle = f"1:{min(device.id, 9999)}"
        _run("tc", "qdisc", "add", "dev", iface, "handle", f"{handle}:", "ingress")
        _run("tc", "filter", "add", "dev", iface, "parent", f"{handle}:",
             "protocol", "ip", "prio", "1", "u32",
             "match", "ip", "src", ip,
             "police", "rate", f"{up_kbps}kbit",
             "burst", f"{max(up_kbps // 8, 10)}k",
             "drop", "flowid", f"{handle}:")

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
    cid = _class_id(device.id)
    _run("tc", "filter", "del", "dev", iface, "parent", "1:", "prio", "1", "u32",
         "match", "ip", "dst", device.ip, "flowid", cid)
    _run("tc", "class", "del", "dev", iface, "classid", cid)
    handle = f"1:{min(device.id, 9999)}"
    _run("tc", "qdisc", "del", "dev", iface, "handle", f"{handle}:", "ingress")


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
