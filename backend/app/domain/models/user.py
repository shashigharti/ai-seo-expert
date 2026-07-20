from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class User(BaseModel):
    id: UUID
    email: EmailStr
    hashed_password: str
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}
