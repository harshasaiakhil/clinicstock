from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class MedicineUnitBase(BaseModel):
    name: str
    code: str
    is_active: bool = True

class MedicineUnitCreate(MedicineUnitBase):
    pass

class MedicineUnitUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    is_active: Optional[bool] = None

class MedicineUnitResponse(MedicineUnitBase):
    id: UUID
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
