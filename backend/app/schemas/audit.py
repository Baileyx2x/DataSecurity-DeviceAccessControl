"""审计 schema。"""
from datetime import datetime
from pydantic import BaseModel

class AuditOut(BaseModel):
    id: int
    actor: str
    action: str
    target_device_id: int | None
    reason: str | None
    timestamp: datetime
    class Config: from_attributes = True
