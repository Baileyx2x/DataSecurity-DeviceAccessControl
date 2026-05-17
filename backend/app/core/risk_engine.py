"""风险判定规则引擎 — 加载 rule 表,按设备评估并生成告警,广播 WebSocket。"""

import json
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.device import Device
from ..models.rule import Rule
from ..models.alert import Alert
from ..ws.manager import manager
from ..ws.events import alert_created


OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
    ">":  lambda a, b: a > b,
    "<":  lambda a, b: a < b,
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


def evaluate_device(db: Session, device: Device, rules: list[Rule]) -> list[Alert]:
    """对单个设备运行给定规则列表,返回触发的告警(已落库)。"""
    ctx = {
        "mac": device.mac,
        "ip": device.ip,
        "category": device.category,
        "vendor": device.vendor,
        "hour": datetime.utcnow().hour,
        "status": device.status,
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
