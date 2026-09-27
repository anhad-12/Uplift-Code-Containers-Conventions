from typing import List, Optional

from pydantic import BaseModel, validator


class OrderIn(BaseModel):
    user_id: int
    items: List[float]
    note: Optional[str] = None
    tags: List[str] = []

    @validator("tags", each_item=True)
    def strip_tag(cls, value):
        return value.strip()


class OrderOut(BaseModel):
    id: int
    user_id: int
    total: float

    class Config:
        orm_mode = True
