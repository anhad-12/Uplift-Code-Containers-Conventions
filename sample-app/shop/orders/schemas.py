from typing import List, Optional

from pydantic import BaseModel, field_validator
from pydantic.config import ConfigDict


class OrderIn(BaseModel):
    user_id: int
    items: List[float]
    note: Optional[str] = None
    tags: List[str] = []

    @field_validator("tags", mode="before")
    @classmethod
    def strip_tag(cls, value):
        if isinstance(value, list):
            return [v.strip() if isinstance(v, str) else v for v in value]
        return value


class OrderOut(BaseModel):
    id: int
    user_id: int
    total: float

    model_config = ConfigDict(from_attributes=True)
