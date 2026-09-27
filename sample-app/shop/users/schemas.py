from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class UserOut(BaseModel):
    id: int
    name: str
    email: Annotated[str, StringConstraints(pattern=r"^[^@]+@[^@]+$")]

    model_config = ConfigDict(from_attributes=True)
