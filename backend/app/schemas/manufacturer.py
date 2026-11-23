from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class ManufacturerBase(BaseModel):
    name: str
    description: Optional[str] = None

class ManufacturerCreate(ManufacturerBase):
    pass

class ManufacturerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ManufacturerResponse(ManufacturerBase):
    id: UUID
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
