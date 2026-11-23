from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime, date
from typing import Optional, List

from app.schemas.branch import BranchResponse
from app.schemas.supplier import SupplierResponse
from app.schemas.user import UserResponse, UserSummaryResponse

# Minimal medicine response schema to avoid circular imports
class MedicineMinResponse(BaseModel):
    id: UUID
    name: str
    generic_name: Optional[str] = None
    quantity: int
    selling_price: float
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class InventorySummaryResponse(BaseModel):
    id: UUID
    medicine_id: UUID
    branch_id: UUID
    total_quantity: int
    available_quantity: int
    reserved_quantity: int
    min_stock_level: int
    max_stock_level: int
    reorder_level: int
    
    # Location
    building: Optional[str] = None
    room: Optional[str] = None
    cupboard: Optional[str] = None
    rack: Optional[str] = None
    shelf: Optional[str] = None
    row: Optional[str] = None
    column: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    medicine: Optional[MedicineMinResponse] = None
    branch: Optional[BranchResponse] = None

    model_config = ConfigDict(from_attributes=True)

class InventorySummaryUpdate(BaseModel):
    min_stock_level: Optional[int] = Field(None, ge=0)
    max_stock_level: Optional[int] = Field(None, ge=0)
    reorder_level: Optional[int] = Field(None, ge=0)
    building: Optional[str] = Field(None, max_length=100)
    room: Optional[str] = Field(None, max_length=100)
    cupboard: Optional[str] = Field(None, max_length=100)
    rack: Optional[str] = Field(None, max_length=100)
    shelf: Optional[str] = Field(None, max_length=100)
    row: Optional[str] = Field(None, max_length=100)
    column: Optional[str] = Field(None, max_length=100)

class InventoryBatchResponse(BaseModel):
    id: UUID
    inventory_summary_id: UUID
    batch_number: str
    supplier_id: Optional[UUID] = None
    purchase_date: Optional[date] = None
    expiry_date: Optional[date] = None
    purchase_price: float
    selling_price: float
    quantity: int
    
    # Location
    building: Optional[str] = None
    room: Optional[str] = None
    cupboard: Optional[str] = None
    rack: Optional[str] = None
    shelf: Optional[str] = None
    row: Optional[str] = None
    column: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    supplier: Optional[SupplierResponse] = None
    summary: Optional[InventorySummaryResponse] = None

    model_config = ConfigDict(from_attributes=True)

class InventoryBatchUpdate(BaseModel):
    selling_price: Optional[float] = Field(None, ge=0.0)
    quantity: Optional[int] = Field(None, ge=0)
    batch_number: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[date] = None
    building: Optional[str] = Field(None, max_length=100)
    room: Optional[str] = Field(None, max_length=100)
    cupboard: Optional[str] = Field(None, max_length=100)
    rack: Optional[str] = Field(None, max_length=100)
    shelf: Optional[str] = Field(None, max_length=100)
    row: Optional[str] = Field(None, max_length=100)
    column: Optional[str] = Field(None, max_length=100)

# Transaction Payloads
class StockInPayload(BaseModel):
    medicine_id: UUID
    branch_id: UUID
    batch_number: str = Field(..., min_length=1, max_length=100)
    supplier_id: Optional[UUID] = None
    purchase_date: Optional[date] = None
    expiry_date: Optional[date] = None
    purchase_price: float = Field(..., ge=0.0)
    selling_price: float = Field(..., ge=0.0)
    quantity: int = Field(..., gt=0)
    
    # Storage Location
    building: Optional[str] = Field(None, max_length=100)
    room: Optional[str] = Field(None, max_length=100)
    cupboard: Optional[str] = Field(None, max_length=100)
    rack: Optional[str] = Field(None, max_length=100)
    shelf: Optional[str] = Field(None, max_length=100)
    row: Optional[str] = Field(None, max_length=100)
    column: Optional[str] = Field(None, max_length=100)
    
    reason: Optional[str] = Field(None, max_length=255)

class DispensePayload(BaseModel):
    batch_id: UUID
    quantity: int = Field(..., gt=0)
    reason: Optional[str] = Field(None, max_length=255)

class TransferPayload(BaseModel):
    batch_id: UUID
    to_branch_id: UUID
    quantity: int = Field(..., gt=0)
    reason: Optional[str] = Field(None, max_length=255)

class AdjustmentPayload(BaseModel):
    batch_id: UUID
    quantity_changed: int = Field(...)  # Positive or negative
    transaction_type: str = Field(..., description="Adjustment | Expired | Damaged")
    reason: Optional[str] = Field(None, max_length=255)

class StockTransactionResponse(BaseModel):
    id: UUID
    user_id: UUID
    branch_id: UUID
    batch_id: UUID
    quantity_changed: int
    transaction_type: str
    reason: Optional[str] = None
    timestamp: datetime
    
    batch: Optional[InventoryBatchResponse] = None
    branch: Optional[BranchResponse] = None
    user: Optional[UserSummaryResponse] = None

    model_config = ConfigDict(from_attributes=True)

class InventorySummaryPaginatedResponse(BaseModel):
    items: List[InventorySummaryResponse]
    page: int
    page_size: int
    total: int
    pages: int

class InventoryBatchPaginatedResponse(BaseModel):
    items: List[InventoryBatchResponse]
    page: int
    page_size: int
    total: int
    pages: int

class StockTransactionPaginatedResponse(BaseModel):
    items: List[StockTransactionResponse]
    page: int
    page_size: int
    total: int
    pages: int
