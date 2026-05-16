"""审计日志路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..models.base import get_session
from ..models.audit_log import AuditLog

router = APIRouter()

@router.get("")
def list_audit(limit: int = 200, db: Session = Depends(get_session)):
    rows = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
    return [r.__dict__ for r in rows]
