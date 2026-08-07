from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional

from app.api import deps
from app.crud import inventory as crud_inventory
from app.services import inventory as service_inventory
from app.schemas.inventory import (
    InventorySummaryResponse,
    InventorySummaryUpdate,
    InventoryBatchResponse,
    InventoryBatchUpdate,
    StockInPayload,
    DispensePayload,
    TransferPayload,
    AdjustmentPayload,
    StockTransactionResponse,
)
from app.models.user import User

router = APIRouter()

# --- Inventory Summary Endpoints ---

@router.get("/summaries", response_model=List[InventorySummaryResponse])
async def list_inventory_summaries(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    search: Optional[str] = None,
    branch_id: Optional[UUID] = None,
    is_low_stock: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[InventorySummaryResponse]:
    """
    Retrieve inventory summaries with optional search (medicine name), branch filter, low stock filter, and pagination (Doctors and Assistants).
    """
    return await crud_inventory.get_inventory_summaries(
        db, search=search, branch_id=branch_id, is_low_stock=is_low_stock, skip=skip, limit=limit
    )

@router.get("/summaries/{summary_id}", response_model=InventorySummaryResponse)
async def get_inventory_summary(
    summary_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> InventorySummaryResponse:
    """
    Get inventory summary details by ID (Doctors and Assistants).
    """
    summary = await crud_inventory.get_inventory_summary(db, summary_id=summary_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory summary not found"
        )
    return summary

@router.put("/summaries/{summary_id}", response_model=InventorySummaryResponse)
async def update_inventory_summary(
    summary_id: UUID,
    summary_in: InventorySummaryUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_doctor),
) -> InventorySummaryResponse:
    """
    Update inventory summary parameters (min stock, default storage locations) (Doctors only).
    """
    summary = await crud_inventory.update_inventory_summary(
        db, summary_id=summary_id, summary_update=summary_in
    )
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory summary not found"
        )
    return summary


# --- Inventory Batch Endpoints ---

@router.get("/batches", response_model=List[InventoryBatchResponse])
async def list_inventory_batches(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    summary_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    is_expired: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[InventoryBatchResponse]:
    """
    Retrieve inventory batches with summary, branch, expiration filter, and pagination (Doctors and Assistants).
    """
    return await crud_inventory.get_inventory_batches(
        db, summary_id=summary_id, branch_id=branch_id, is_expired=is_expired, skip=skip, limit=limit
    )

@router.get("/batches/{batch_id}", response_model=InventoryBatchResponse)
async def get_inventory_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> InventoryBatchResponse:
    """
    Get inventory batch details by ID (Doctors and Assistants).
    """
    batch = await crud_inventory.get_inventory_batch(db, batch_id=batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory batch not found"
        )
    return batch

@router.put("/batches/{batch_id}", response_model=InventoryBatchResponse)
async def update_inventory_batch(
    batch_id: UUID,
    batch_in: InventoryBatchUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_doctor),
) -> InventoryBatchResponse:
    """
    Update inventory batch details (selling price, storage locations) (Doctors only).
    """
    batch = await crud_inventory.update_inventory_batch(
        db, batch_id=batch_id, batch_update=batch_in
    )
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory batch not found"
        )
    return batch


# --- Stock Transaction Endpoints ---

@router.post("/stock-in", response_model=StockTransactionResponse, status_code=status.HTTP_201_CREATED)
async def stock_in(
    payload: StockInPayload,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_doctor),
) -> StockTransactionResponse:
    """
    Receive stock into a branch batch (Doctors only).
    """
    tx = await service_inventory.perform_stock_in(db, payload=payload, user_id=current_user.id)
    return await crud_inventory.get_transaction_with_details(db, tx.id)

@router.post("/dispense", response_model=StockTransactionResponse, status_code=status.HTTP_201_CREATED)
async def dispense(
    payload: DispensePayload,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> StockTransactionResponse:
    """
    Dispense medicine from a branch batch (accessible by Doctors and Assistants).
    """
    tx = await service_inventory.perform_dispense(db, payload=payload, user_id=current_user.id)
    return await crud_inventory.get_transaction_with_details(db, tx.id)

@router.post("/transfer", response_model=List[StockTransactionResponse], status_code=status.HTTP_201_CREATED)
async def transfer(
    payload: TransferPayload,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_doctor),
) -> List[StockTransactionResponse]:
    """
    Transfer stock from one branch batch to another branch (Doctors only).
    """
    tx_out, tx_in = await service_inventory.perform_transfer(db, payload=payload, user_id=current_user.id)
    tx_out_details = await crud_inventory.get_transaction_with_details(db, tx_out.id)
    tx_in_details = await crud_inventory.get_transaction_with_details(db, tx_in.id)
    return [tx_out_details, tx_in_details]

@router.post("/adjust", response_model=StockTransactionResponse, status_code=status.HTTP_201_CREATED)
async def adjust_stock(
    payload: AdjustmentPayload,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_doctor),
) -> StockTransactionResponse:
    """
    Adjust stock level of a batch (Adjustment, Expired, Damaged) (Doctors only).
    """
    tx = await service_inventory.perform_adjustment(db, payload=payload, user_id=current_user.id)
    return await crud_inventory.get_transaction_with_details(db, tx.id)

@router.get("/transactions", response_model=List[StockTransactionResponse])
async def list_transactions(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    branch_id: Optional[UUID] = None,
    transaction_type: Optional[str] = None,
    batch_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[StockTransactionResponse]:
    """
    Retrieve stock transaction history with optional filters (Doctors and Assistants).
    """
    return await crud_inventory.get_transactions(
        db,
        branch_id=branch_id,
        transaction_type=transaction_type,
        batch_id=batch_id,
        skip=skip,
        limit=limit,
    )
