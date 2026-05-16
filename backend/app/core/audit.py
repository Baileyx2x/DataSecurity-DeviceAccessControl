"""审计模块 — 所有写操作必须经此处统一落盘。"""

from sqlalchemy.orm import Session
from ..models.audit_log import AuditLog


def write_audit(db: Session, actor: str, action: str,
                target_device_id: int | None = None, reason: str | None = None) -> AuditLog:
    log = AuditLog(actor=actor, action=action, target_device_id=target_device_id, reason=reason)
    db.add(log)
    db.commit()
    return log
