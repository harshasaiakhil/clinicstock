from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List

from app.schemas.category import CategoryResponse
from app.schemas.manufacturer import ManufacturerResponse
from app.schemas.potency import PotencyResponse
from app.schemas.medicine_unit import MedicineUnitResponse

class MedicineBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    generic_name: Optional[str] = Field(None, max_length=150)
    category_id: UUID
    manufacturer_id: Optional[UUID] = None
    potency_id: UUID
    unit_id: UUID
    quantity: int = Field(0, ge=0)
    selling_price: float = Field(..., ge=0.0)
    gst_percentage: float = Field(0.0, ge=0.0)
    hsn_code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=255)
    image_url: Optional[str] = Field(None, max_length=255)
    barcode: Optional[str] = Field(None, max_length=50)
    qr_code: Optional[str] = Field(None, max_length=100)
    is_active: bool = True

class MedicineCreate(MedicineBase):
    pass

class MedicineUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    generic_name: Optional[str] = Field(None, max_length=150)
    category_id: Optional[UUID] = None
    manufacturer_id: Optional[UUID] = None
    potency_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None
    quantity: Optional[int] = Field(None, ge=0)
    selling_price: Optional[float] = Field(None, ge=0.0)
    gst_percentage: Optional[float] = Field(None, ge=0.0)
    hsn_code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=255)
    image_url: Optional[str] = Field(None, max_length=255)
    barcode: Optional[str] = Field(None, max_length=50)
    qr_code: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None

# Lightweight item schema for list views (avoids eager loading deep nested summaries & batches)
class MedicineListItemResponse(MedicineBase):
    id: UUID
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    category: Optional[CategoryResponse] = None
    manufacturer: Optional[ManufacturerResponse] = None
    potency: Optional[PotencyResponse] = None
    unit: Optional[MedicineUnitResponse] = None
    warning: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# Standard full response for single medicine detail
class MedicineResponse(MedicineListItemResponse):
    pass

# Paginated response envelope
class MedicinePaginatedResponse(BaseModel):
    items: List[MedicineListItemResponse]
    page: int
    page_size: int
    total: int
    pages: int

class MedicineImportSummary(BaseModel):
    imported: int = 0
    updated: int = 0
    failed: int = 0
    duplicate_rows: int = 0
    errors: List[str] = []
