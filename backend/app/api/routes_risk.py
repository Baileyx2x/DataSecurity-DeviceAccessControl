"""告警 + 规则路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..models.base import get_session
from ..models.alert import Alert
from ..models.rule import Rule

router = APIRouter()

@router.get("/alerts")
def list_alerts(status: str | None = None, db: Session = Depends(get_session)):
    q = db.query(Alert)
    if status: q = q.filter(Alert.status == status)
    return [a.__dict__ for a in q.all()]

@router.post("/alerts/{alert_id}/ack")
def ack_alert(alert_id: int, db: Session = Depends(get_session)):
    a = db.get(Alert, alert_id)
    a.status = "acknowledged"
    db.commit()
    return {"ok": True}

@router.get("/rules")
def list_rules(db: Session = Depends(get_session)):
    return [r.__dict__ for r in db.query(Rule).all()]
