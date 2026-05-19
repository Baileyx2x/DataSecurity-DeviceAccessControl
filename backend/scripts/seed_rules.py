"""灌入默认风险规则。"""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.models.base import SessionLocal, init_db
from app.models.rule import Rule

DEFAULTS = [
    {
        "name": "未知设备夜间接入",
        "description": "未登记设备在 0~6 点或 23 点出现",
        "condition_json": json.dumps({"all": [
            {"field": "category", "op": "==", "value": "unknown"},
            {"field": "hour",     "op": "in", "value": [0,1,2,3,4,5,23]},
        ]}),
        "action": "alert", "level": 2,
    },
    {
        "name": "黑名单设备出现",
        "description": "黑名单设备一旦上线立即阻断",
        "condition_json": json.dumps({"field": "category", "op": "==", "value": "black"}),
        "action": "block", "level": 3,
    },
    {
        "name": "陌生设备首次接入",
        "description": "不在白名单也不在黑名单的设备第一次出现在网络中",
        "condition_json": json.dumps({"all": [
            {"field": "category", "op": "==", "value": "unknown"},
            {"field": "is_new",   "op": "==", "value": True},
        ]}),
        "action": "alert", "level": 2,
    },
    {
        "name": "设备频繁上下线",
        "description": "1 分钟内断开/重连超过 3 次(6 次状态变更),可能存在攻击或网络不稳定",
        "condition_json": json.dumps({"field": "flip_count_1min", "op": ">=", "value": 6}),
        "action": "alert", "level": 2,
    },
    {
        "name": "设备端口扫描行为",
        "description": "短时间内访问大量不同 IP 或端口,典型的扫描/探测行为",
        "condition_json": json.dumps({"any": [
            {"field": "unique_ports_5min", "op": ">=", "value": 30},
            {"field": "unique_ips_5min",   "op": ">=", "value": 15},
        ]}),
        "action": "block", "level": 3,
    },
]

init_db()
db = SessionLocal()
for r in DEFAULTS:
    if not db.query(Rule).filter(Rule.name == r["name"]).first():
        db.add(Rule(**r))
db.commit()
print(f"✅ seeded {len(DEFAULTS)} default rules")
