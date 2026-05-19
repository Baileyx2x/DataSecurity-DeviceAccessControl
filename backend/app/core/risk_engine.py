"""风险判定规则引擎 — 加载 rule 表,按设备评估并生成告警,广播 WebSocket。"""

import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.device import Device
from ..models.rule import Rule
from ..models.alert import Alert
from ..models.access_log import AccessLog
from ..models.traffic import DeviceTraffic
from ..ws.manager import manager
from ..ws.events import alert_created


OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
    ">":  lambda a, b: a > b,
    "<":  lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
}


def _eval_condition(cond: dict, ctx: dict) -> bool:
    if "all" in cond:
        return all(_eval_condition(c, ctx) for c in cond["all"])
    if "any" in cond:
        return any(_eval_condition(c, ctx) for c in cond["any"])
    field, op, value = cond["field"], cond["op"], cond["value"]
    return OPS[op](ctx.get(field), value)


def load_enabled_rules(db: Session) -> list[Rule]:
    """加载所有启用的规则(调用方缓存,避免 N+1)。"""
    return db.query(Rule).filter(Rule.enabled == True).all()  # noqa: E712


def _count_recent_flips(db: Session, device_id: int, window_sec: int = 60) -> int:
    """统计设备在最近 window_sec 秒内的上下线事件次数。"""
    cutoff = datetime.now() - timedelta(seconds=window_sec)
    return db.query(AccessLog).filter(
        AccessLog.device_id == device_id,
        AccessLog.timestamp >= cutoff,
        AccessLog.event_type.in_(["online", "offline"]),
    ).count()


def _traffic_scan_metrics(db: Session, device_id: int, window_sec: int = 300) -> tuple[int, int]:
    """统计设备在最近 window_sec 秒内累计访问的不同目的 IP 数和端口数。"""
    cutoff = datetime.now() - timedelta(seconds=window_sec)
    rows = db.query(
        DeviceTraffic.unique_dst_ips, DeviceTraffic.unique_dst_ports
    ).filter(
        DeviceTraffic.device_id == device_id,
        DeviceTraffic.sample_at >= cutoff,
    ).all()
    total_ips = sum(r[0] or 0 for r in rows)
    total_ports = sum(r[1] or 0 for r in rows)
    return total_ips, total_ports


def evaluate_device(db: Session, device: Device, rules: list[Rule]) -> list[Alert]:
    """对单个设备运行给定规则列表,返回触发的告警(已落库)。"""
    now = datetime.now()
    scan_window = timedelta(seconds=120)  # first_seen 在此窗口内视为"首次出现"
    flip_count = _count_recent_flips(db, device.id)
    scan_ips, scan_ports = _traffic_scan_metrics(db, device.id)

    ctx = {
        "mac": device.mac,
        "ip": device.ip,
        "category": device.category,
        "vendor": device.vendor,
        "hour": now.hour,
        "status": device.status,
        "is_new": (now - device.first_seen) <= scan_window,
        "flip_count_1min": flip_count,
        "unique_ips_5min": scan_ips,
        "unique_ports_5min": scan_ports,
    }
    triggered: list[Alert] = []
    for rule in rules:
        cond = json.loads(rule.condition_json)
        if _eval_condition(cond, ctx):
            a = Alert(device_id=device.id, rule_id=rule.id, level=rule.level,
                      message=f"规则触发: {rule.name}")
            db.add(a)
            triggered.append(a)
            device.risk_level = max(device.risk_level, rule.level)
    db.commit()

    for a in triggered:
        manager.broadcast_sync(alert_created(a))

    return triggered
