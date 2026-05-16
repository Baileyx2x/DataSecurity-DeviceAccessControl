"""规则 schema。"""
from pydantic import BaseModel

class RuleIn(BaseModel):
    name: str
    description: str | None = None
    condition_json: str
    action: str = "alert"   # alert / block
    level: int = 1
    enabled: bool = True

class RuleOut(RuleIn):
    id: int
    class Config: from_attributes = True
