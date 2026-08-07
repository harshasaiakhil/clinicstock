from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import List, Optional
from app.schemas.inventory import StockTransactionResponse

class BranchStatsResponse(BaseModel):
    branch_id: UUID
    branch_name: str
    branch_code: str
    total_inventory_items: int
    total_inventory_value: float
    low_stock_count: int

    model_config = ConfigDict(from_attributes=True)

class TopMedicineResponse(BaseModel):
    medicine_id: UUID
    name: str
    generic_name: Optional[str] = None
    value: int  # quantity dispensed or available stock

    model_config = ConfigDict(from_attributes=True)

class DashboardStatsResponse(BaseModel):
    # Medicine Counts
    total_medicines: int
    total_active_medicines: int
    
    # Inventory metrics
    total_inventory_items: int
    total_inventory_value: float
    low_stock_count: int
    out_of_stock_count: int
    
    # Expiry tracking
    expiring_30_days_count: int
    expired_count: int
    
    # Today's activity
    todays_stock_in: int
    todays_dispensed: int
    todays_transfers: int
    todays_adjustments: int
    todays_damaged: int
    
    # Breakdowns
    branch_wise_stats: List[BranchStatsResponse] = []
    top_dispensed_medicines: List[TopMedicineResponse] = []
    top_low_stock_medicines: List[TopMedicineResponse] = []
    recent_activity: List[StockTransactionResponse] = []

    model_config = ConfigDict(from_attributes=True)
