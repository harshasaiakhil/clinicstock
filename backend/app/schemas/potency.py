from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class PotencyBase(BaseModel):
    name: str
    is_active: bool = True

class PotencyCreate(PotencyBase):
    pass

class PotencyUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class PotencyResponse(PotencyBase):
    id: UUID
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
