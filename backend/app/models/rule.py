"""风险判定规则表。

condition_json 示例:
  {"all": [
    {"field": "category", "op": "==", "value": "unknown"},
    {"field": "hour",     "op": "in", "value": [0,1,2,3,4,5,23]}
  ]}
"""

from sqlalchemy import String, Integer, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Rule(Base):
    __tablename__ = "rule"

    id:             Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:           Mapped[str]  = mapped_column(String(128), unique=True)
    description:    Mapped[str | None] = mapped_column(Text, nullable=True)
    condition_json: Mapped[str]  = mapped_column(Text)        # 规则 DSL (JSON 字符串)
    action:         Mapped[str]  = mapped_column(String(16))  # alert / block
    level:          Mapped[int]  = mapped_column(Integer, default=1)  # 0~3
    enabled:        Mapped[bool] = mapped_column(Boolean, default=True)
