"""告警 schema。"""
from datetime import datetime
from pydantic import BaseModel

class AlertOut(BaseModel):
    id: int
    device_id: int
    rule_id: int | None
    level: int
    message: str
    status: str
    created_at: datetime
    class Config: from_attributes = True
