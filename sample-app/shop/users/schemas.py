from typing import Annotated
from pydantic import BaseModel, StringConstraints
from pydantic import ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: Annotated[str, StringConstraints(pattern=r"^[^@]+@[^@]+$")]
