"""告警 + 规则路由 — CRUD 完整。"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..models.base import get_session
from ..models.alert import Alert
from ..models.rule import Rule

router = APIRouter()

# ===== 告警 =====

@router.get("/alerts")
def list_alerts(status: str | None = None, device_id: int | None = None,
                db: Session = Depends(get_session)):
    q = db.query(Alert)
    if status:    q = q.filter(Alert.status == status)
    if device_id: q = q.filter(Alert.device_id == device_id)
    return [a.__dict__ for a in q.order_by(Alert.created_at.desc()).all()]


@router.post("/alerts/{alert_id}/ack")
def ack_alert(alert_id: int, db: Session = Depends(get_session)):
    a = db.get(Alert, alert_id)
    if not a: raise HTTPException(404)
    a.status = "acknowledged"
    db.commit()
    return {"ok": True}


@router.post("/alerts/{alert_id}/close")
def close_alert(alert_id: int, db: Session = Depends(get_session)):
    a = db.get(Alert, alert_id)
    if not a: raise HTTPException(404)
    a.status = "closed"
    db.commit()
    return {"ok": True}


# ===== 规则 =====

@router.get("/rules")
def list_rules(db: Session = Depends(get_session)):
    return [r.__dict__ for r in db.query(Rule).order_by(Rule.name).all()]


@router.post("/rules")
def create_rule(data: dict, db: Session = Depends(get_session)):
    required = ["name", "condition_json", "action", "level"]
    for key in required:
        if key not in data:
            raise HTTPException(400, f"missing field: {key}")
    # 校验 JSON
    try:
        json.loads(data["condition_json"])
    except json.JSONDecodeError:
        raise HTTPException(400, "condition_json 不是合法 JSON")
    if data["action"] not in ("alert", "block"):
        raise HTTPException(400, "action 必须是 alert 或 block")
    if not (0 <= int(data["level"]) <= 3):
        raise HTTPException(400, "level 必须在 0~3 之间")

    r = Rule(
        name=data["name"],
        description=data.get("description", ""),
        condition_json=data["condition_json"],
        action=data["action"],
        level=int(data["level"]),
        enabled=data.get("enabled", True),
    )
    db.add(r)
    db.commit()
    return r.__dict__


@router.put("/rules/{rule_id}")
def update_rule(rule_id: int, data: dict, db: Session = Depends(get_session)):
    r = db.get(Rule, rule_id)
    if not r: raise HTTPException(404)
    if "name" in data:           r.name = data["name"]
    if "description" in data:    r.description = data["description"]
    if "condition_json" in data:
        try:
            json.loads(data["condition_json"])
        except json.JSONDecodeError:
            raise HTTPException(400, "condition_json 不是合法 JSON")
        r.condition_json = data["condition_json"]
    if "action" in data:
        if data["action"] not in ("alert", "block"):
            raise HTTPException(400, "action 必须是 alert 或 block")
        r.action = data["action"]
    if "level" in data:
        if not (0 <= int(data["level"]) <= 3):
            raise HTTPException(400, "level 必须在 0~3 之间")
        r.level = int(data["level"])
    if "enabled" in data:
        r.enabled = bool(data["enabled"])
    db.commit()
    return r.__dict__


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_session)):
    r = db.get(Rule, rule_id)
    if not r: raise HTTPException(404)
    db.delete(r)
    db.commit()
    return {"ok": True}


@router.post("/rules/{rule_id}/toggle")
def toggle_rule(rule_id: int, db: Session = Depends(get_session)):
    r = db.get(Rule, rule_id)
    if not r: raise HTTPException(404)
    r.enabled = not r.enabled
    db.commit()
    return {"enabled": r.enabled}
