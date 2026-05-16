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
]

init_db()
db = SessionLocal()
for r in DEFAULTS:
    if not db.query(Rule).filter(Rule.name == r["name"]).first():
        db.add(Rule(**r))
db.commit()
print(f"✅ seeded {len(DEFAULTS)} default rules")
