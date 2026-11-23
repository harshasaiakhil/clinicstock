from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional, Union
from datetime import datetime

from app.api import deps
from app.crud import inventory as crud_inventory
from app.services import inventory as service_inventory
from app.schemas.inventory import (
    InventorySummaryResponse,
    InventorySummaryPaginatedResponse,
    InventorySummaryUpdate,
    InventoryBatchResponse,
    InventoryBatchPaginatedResponse,
    InventoryBatchUpdate,
    StockInPayload,
    DispensePayload,
    TransferPayload,
    AdjustmentPayload,
    StockTransactionResponse,
    StockTransactionPaginatedResponse,
)
from app.models.user import User

router = APIRouter()

# --- Inventory Summary Endpoints ---

@router.get("/summaries", response_model=InventorySummaryPaginatedResponse)
async def list_inventory_summaries(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    search: Optional[str] = None,
    branch_id: Optional[UUID] = None,
    category_id: Optional[UUID] = None,
    is_low_stock: Optional[bool] = None,
    page: int = 1,
    page_size: int = 25,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
) -> InventorySummaryPaginatedResponse:
    """
    Retrieve inventory summaries with server-side filtering, branch boundary enforcement, and pagination.
    """
    # Enforce branch boundaries on the server
    effective_branch_id = deps.enforce_branch_access(current_user, branch_id)

    # Support backwards compatibility if skip/limit passed
    if limit is not None and page_size == 25:
        page_size = min(100, max(1, limit))
    if skip is not None and page == 1 and page_size > 0:
        page = (skip // page_size) + 1

    items, total, pages = await crud_inventory.get_inventory_summaries_paginated(
        db,
        search=search,
        branch_id=effective_branch_id,
        category_id=category_id,
        is_low_stock=is_low_stock,
        page=page,
        page_size=page_size,
    )
    return InventorySummaryPaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        pages=pages,
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
    # Check branch access for assistants
    deps.enforce_branch_access(current_user, summary.branch_id)
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

@router.get("/batches", response_model=InventoryBatchPaginatedResponse)
async def list_inventory_batches(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    summary_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    is_expired: Optional[bool] = None,
    page: int = 1,
    page_size: int = 25,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
) -> InventoryBatchPaginatedResponse:
    """
    Retrieve inventory batches with server-side pagination and branch boundary enforcement.
    """
    effective_branch_id = deps.enforce_branch_access(current_user, branch_id)

    if limit is not None and page_size == 25:
        page_size = min(100, max(1, limit))
    if skip is not None and page == 1 and page_size > 0:
        page = (skip // page_size) + 1

    items, total, pages = await crud_inventory.get_inventory_batches_paginated(
        db,
        summary_id=summary_id,
        branch_id=effective_branch_id,
        is_expired=is_expired,
        page=page,
        page_size=page_size,
    )
    return InventoryBatchPaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        pages=pages,
    )

@router.get("/batches/{batch_id}", response_model=InventoryBatchResponse)
async def get_inventory_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> InventoryBatchResponse:
    """
    Get inventory batch details by ID.
    """
    batch = await crud_inventory.get_inventory_batch(db, batch_id=batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory batch not found"
        )
    if batch.summary:
        deps.enforce_branch_access(current_user, batch.summary.branch_id)
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
    Dispense medicine from a branch batch (Doctors and Assistants, with server-side branch enforcement).
    """
    tx = await service_inventory.perform_dispense(db, payload=payload, current_user=current_user)
    return await crud_inventory.get_transaction_with_details(db, tx.id)

@router.post("/transfer", response_model=List[StockTransactionResponse], status_code=status.HTTP_201_CREATED)
async def transfer(
    payload: TransferPayload,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_doctor),
) -> List[StockTransactionResponse]:
    """
    Transfer stock atomically between branches in a single transaction (Doctors only).
    """
    tx_out, tx_in = await service_inventory.perform_transfer(db, payload=payload, current_user=current_user)
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
    Adjust stock level of a batch (Adjustment, Expired, Damaged) atomically (Doctors only).
    """
    tx = await service_inventory.perform_adjustment(db, payload=payload, current_user=current_user)
    return await crud_inventory.get_transaction_with_details(db, tx.id)

@router.get("/transactions", response_model=StockTransactionPaginatedResponse)
async def list_transactions(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    branch_id: Optional[UUID] = None,
    transaction_type: Optional[str] = None,
    batch_id: Optional[UUID] = None,
    medicine_id: Optional[UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 25,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
) -> StockTransactionPaginatedResponse:
    """
    Retrieve stock transaction history with server-side pagination, date filtering, and branch boundary enforcement.
    """
    effective_branch_id = deps.enforce_branch_access(current_user, branch_id)

    if limit is not None and page_size == 25:
        page_size = min(100, max(1, limit))
    if skip is not None and page == 1 and page_size > 0:
        page = (skip // page_size) + 1

    items, total, pages = await crud_inventory.get_transactions_paginated(
        db,
        branch_id=effective_branch_id,
        transaction_type=transaction_type,
        batch_id=batch_id,
        medicine_id=medicine_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return StockTransactionPaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        pages=pages,
    )

@router.get("/reports/valuation")
async def get_valuation_report(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    branch_id: Optional[UUID] = None,
):
    """
    SQL-aggregated valuation report returning total items and valuation in INR without loading raw rows into browser.
    """
    effective_branch_id = deps.enforce_branch_access(current_user, branch_id)
    from sqlalchemy import select, func
    from app.models.inventory import InventoryBatch, InventorySummary

    val_query = select(
        func.coalesce(func.sum(InventoryBatch.quantity), 0).label("total_items"),
        func.coalesce(func.sum(InventoryBatch.quantity * InventoryBatch.purchase_price), 0.0).label("total_valuation"),
    ).join(InventoryBatch.summary)

    if effective_branch_id:
        val_query = val_query.where(InventorySummary.branch_id == effective_branch_id)

    res = (await db.execute(val_query)).first()
    return {
        "total_items": int(res.total_items) if res else 0,
        "total_valuation": float(res.total_valuation) if res else 0.0,
        "branch_id": str(effective_branch_id) if effective_branch_id else None,
    }

