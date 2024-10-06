from typing import Optional

from pydantic import BaseModel, Field

class UserSchema(BaseModel):
    id: int
    user_id: int
    username: Optional[str]

    class Config:
        from_attributes = True


class CategoryCreateSchema(BaseModel):
    name: str = Field(..., title="Название категории", min_length=1)