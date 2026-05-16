"""设备 Pydantic schema。"""
from datetime import datetime
from pydantic import BaseModel

class DeviceOut(BaseModel):
    id: int
    mac: str
    ip: str
    hostname: str | None = None
    vendor: str | None = None
    os_guess: str | None = None
    category: str
    risk_level: int
    status: str
    first_seen: datetime
    last_seen: datetime
    note: str | None = None
    class Config: from_attributes = True
