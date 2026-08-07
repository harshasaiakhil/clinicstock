from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from uuid import UUID
from datetime import date
from typing import Tuple, List, Optional

from app.models.inventory import InventorySummary, InventoryBatch, StockTransaction
from app.models.medicine import Medicine
from app.models.branch import Branch
from app.schemas.inventory import StockInPayload, DispensePayload, TransferPayload, AdjustmentPayload

async def get_summary_by_medicine_branch(
    db: AsyncSession, medicine_id: UUID, branch_id: UUID
) -> Optional[InventorySummary]:
    result = await db.execute(
        select(InventorySummary)
        .where(InventorySummary.medicine_id == medicine_id, InventorySummary.branch_id == branch_id)
        .options(selectinload(InventorySummary.batches))
    )
    return result.scalars().first()

async def get_batch_by_id(db: AsyncSession, batch_id: UUID) -> Optional[InventoryBatch]:
    result = await db.execute(
        select(InventoryBatch)
        .where(InventoryBatch.id == batch_id)
        .options(selectinload(InventoryBatch.summary))
    )
    return result.scalars().first()

async def get_batch_by_number(
    db: AsyncSession, summary_id: UUID, batch_number: str
) -> Optional[InventoryBatch]:
    result = await db.execute(
        select(InventoryBatch).where(
            InventoryBatch.inventory_summary_id == summary_id,
            InventoryBatch.batch_number == batch_number,
        )
    )
    return result.scalars().first()

async def get_summary_with_details(
    db: AsyncSession, summary_id: UUID
) -> Optional[InventorySummary]:
    result = await db.execute(
        select(InventorySummary)
        .where(InventorySummary.id == summary_id)
        .options(
            selectinload(InventorySummary.medicine),
            selectinload(InventorySummary.branch),
            selectinload(InventorySummary.batches),
        )
    )
    return result.scalars().first()

async def perform_stock_in(
    db: AsyncSession, payload: StockInPayload, user_id: UUID
) -> StockTransaction:
    # 1. Fetch or create InventorySummary
    summary = await get_summary_by_medicine_branch(db, payload.medicine_id, payload.branch_id)
    if not summary:
        summary = InventorySummary(
            medicine_id=payload.medicine_id,
            branch_id=payload.branch_id,
            total_quantity=0,
            available_quantity=0,
            reserved_quantity=0,
            # Assign storage locations from payload as defaults
            building=payload.building,
            room=payload.room,
            cupboard=payload.cupboard,
            rack=payload.rack,
            shelf=payload.shelf,
            row=payload.row,
            column=payload.column,
        )
        db.add(summary)
        await db.flush()  # Generate ID

    # 2. Fetch or create InventoryBatch
    batch = await get_batch_by_number(db, summary.id, payload.batch_number)
    if not batch:
        batch = InventoryBatch(
            inventory_summary_id=summary.id,
            batch_number=payload.batch_number,
            supplier_id=payload.supplier_id,
            purchase_date=payload.purchase_date,
            expiry_date=payload.expiry_date,
            purchase_price=payload.purchase_price,
            selling_price=payload.selling_price,
            quantity=0,
            building=payload.building,
            room=payload.room,
            cupboard=payload.cupboard,
            rack=payload.rack,
            shelf=payload.shelf,
            row=payload.row,
            column=payload.column,
        )
        db.add(batch)
        await db.flush()
    else:
        # Update existing batch prices/dates/locations
        if payload.supplier_id:
            batch.supplier_id = payload.supplier_id
        if payload.purchase_date:
            batch.purchase_date = payload.purchase_date
        if payload.expiry_date:
            batch.expiry_date = payload.expiry_date
        batch.purchase_price = payload.purchase_price
        batch.selling_price = payload.selling_price
        # Update locations if provided
        if payload.building:
            batch.building = payload.building
        if payload.room:
            batch.room = payload.room
        if payload.cupboard:
            batch.cupboard = payload.cupboard
        if payload.rack:
            batch.rack = payload.rack
        if payload.shelf:
            batch.shelf = payload.shelf
        if payload.row:
            batch.row = payload.row
        if payload.column:
            batch.column = payload.column

    # 3. Increment quantities
    batch.quantity += payload.quantity
    summary.total_quantity += payload.quantity
    summary.available_quantity += payload.quantity

    # 4. Log transaction
    tx = StockTransaction(
        user_id=user_id,
        branch_id=payload.branch_id,
        batch_id=batch.id,
        quantity_changed=payload.quantity,
        transaction_type="Stock In",
        reason=payload.reason,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx

async def perform_dispense(
    db: AsyncSession, payload: DispensePayload, user_id: UUID
) -> StockTransaction:
    # 1. Fetch batch
    batch = await get_batch_id_with_summary(db, payload.batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory batch not found")

    # 2. Check Expiry
    if batch.expiry_date and batch.expiry_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot dispense expired medicine. Batch is expired.",
        )

    # 3. Check Quantity
    if batch.quantity < payload.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock in batch. Available: {batch.quantity}",
        )

    # 4. Deduct quantities
    batch.quantity -= payload.quantity
    summary = batch.summary
    summary.total_quantity -= payload.quantity
    summary.available_quantity -= payload.quantity

    # 5. Log transaction
    tx = StockTransaction(
        user_id=user_id,
        branch_id=summary.branch_id,
        batch_id=batch.id,
        quantity_changed=-payload.quantity,
        transaction_type="Dispense",
        reason=payload.reason,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx

async def perform_transfer(
    db: AsyncSession, payload: TransferPayload, user_id: UUID
) -> Tuple[StockTransaction, StockTransaction]:
    # 1. Get source batch
    source_batch = await get_batch_id_with_summary(db, payload.batch_id)
    if not source_batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source batch not found")

    source_summary = source_batch.summary
    if source_summary.branch_id == payload.to_branch_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination branches cannot be the same.",
        )

    # 2. Validate quantity
    if source_batch.quantity < payload.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock in source batch. Available: {source_batch.quantity}",
        )

    # 3. Deduct from source
    source_batch.quantity -= payload.quantity
    source_summary.total_quantity -= payload.quantity
    source_summary.available_quantity -= payload.quantity

    # Log Transfer Out Transaction
    tx_out = StockTransaction(
        user_id=user_id,
        branch_id=source_summary.branch_id,
        batch_id=source_batch.id,
        quantity_changed=-payload.quantity,
        transaction_type="Transfer Out",
        reason=payload.reason,
    )
    db.add(tx_out)
    await db.flush()

    # 4. Fetch or create destination Summary
    dest_summary = await get_summary_by_medicine_branch(
        db, source_summary.medicine_id, payload.to_branch_id
    )
    if not dest_summary:
        dest_summary = InventorySummary(
            medicine_id=source_summary.medicine_id,
            branch_id=payload.to_branch_id,
            total_quantity=0,
            available_quantity=0,
            reserved_quantity=0,
            building=source_batch.building,
            room=source_batch.room,
            cupboard=source_batch.cupboard,
            rack=source_batch.rack,
            shelf=source_batch.shelf,
            row=source_batch.row,
            column=source_batch.column,
        )
        db.add(dest_summary)
        await db.flush()

    # 5. Fetch or create destination Batch
    dest_batch = await get_batch_by_number(db, dest_summary.id, source_batch.batch_number)
    if not dest_batch:
        dest_batch = InventoryBatch(
            inventory_summary_id=dest_summary.id,
            batch_number=source_batch.batch_number,
            supplier_id=source_batch.supplier_id,
            purchase_date=source_batch.purchase_date,
            expiry_date=source_batch.expiry_date,
            purchase_price=source_batch.purchase_price,
            selling_price=source_batch.selling_price,
            quantity=0,
            building=source_batch.building,
            room=source_batch.room,
            cupboard=source_batch.cupboard,
            rack=source_batch.rack,
            shelf=source_batch.shelf,
            row=source_batch.row,
            column=source_batch.column,
        )
        db.add(dest_batch)
        await db.flush()

    # 6. Increment destination
    dest_batch.quantity += payload.quantity
    dest_summary.total_quantity += payload.quantity
    dest_summary.available_quantity += payload.quantity

    # Log Transfer In Transaction
    tx_in = StockTransaction(
        user_id=user_id,
        branch_id=payload.to_branch_id,
        batch_id=dest_batch.id,
        quantity_changed=payload.quantity,
        transaction_type="Transfer In",
        reason=payload.reason,
    )
    db.add(tx_in)
    await db.commit()
    await db.refresh(tx_out)
    await db.refresh(tx_in)
    return tx_out, tx_in

async def perform_adjustment(
    db: AsyncSession, payload: AdjustmentPayload, user_id: UUID
) -> StockTransaction:
    # 1. Fetch batch
    batch = await get_batch_id_with_summary(db, payload.batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory batch not found")

    # 2. Check final quantity
    if batch.quantity + payload.quantity_changed < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Adjustment results in negative stock. Current quantity: {batch.quantity}",
        )

    # 3. Apply changes
    batch.quantity += payload.quantity_changed
    summary = batch.summary
    summary.total_quantity += payload.quantity_changed
    summary.available_quantity += payload.quantity_changed

    # 4. Log transaction
    tx = StockTransaction(
        user_id=user_id,
        branch_id=summary.branch_id,
        batch_id=batch.id,
        quantity_changed=payload.quantity_changed,
        transaction_type=payload.transaction_type,
        reason=payload.reason,
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx

async def get_batch_id_with_summary(db: AsyncSession, batch_id: UUID) -> Optional[InventoryBatch]:
    result = await db.execute(
        select(InventoryBatch)
        .where(InventoryBatch.id == batch_id)
        .options(selectinload(InventoryBatch.summary))
    )
    return result.scalars().first()
