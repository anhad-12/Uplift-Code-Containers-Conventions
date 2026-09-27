from pydantic import BaseModel, constr


class UserOut(BaseModel):
    id: int
    name: str
    email: constr(regex=r"^[^@]+@[^@]+$")

    class Config:
        orm_mode = True
