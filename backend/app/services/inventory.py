from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from uuid import UUID
from datetime import date
from typing import Tuple, Optional

from app.models.inventory import InventorySummary, InventoryBatch, StockTransaction
from app.models.user import User
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
            building=payload.building,
            room=payload.room,
            cupboard=payload.cupboard,
            rack=payload.rack,
            shelf=payload.shelf,
            row=payload.row,
            column=payload.column,
        )
        db.add(summary)
        await db.flush()

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
            quantity=payload.quantity,
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
        # Preserve historical valuation using weighted average purchase price if restocked
        if batch.quantity > 0 and float(batch.purchase_price) != float(payload.purchase_price):
            total_cost = (batch.quantity * float(batch.purchase_price)) + (payload.quantity * float(payload.purchase_price))
            new_qty = batch.quantity + payload.quantity
            batch.purchase_price = round(total_cost / new_qty, 2)
        elif batch.quantity == 0:
            batch.purchase_price = payload.purchase_price

        batch.selling_price = payload.selling_price
        batch.quantity += payload.quantity

        if payload.supplier_id:
            batch.supplier_id = payload.supplier_id
        if payload.purchase_date:
            batch.purchase_date = payload.purchase_date
        if payload.expiry_date:
            batch.expiry_date = payload.expiry_date

        if payload.cupboard:
            batch.cupboard = payload.cupboard
        if payload.rack:
            batch.rack = payload.rack
        if payload.row:
            batch.row = payload.row
        if payload.column:
            batch.column = payload.column

    # 3. Update summary
    summary.total_quantity += payload.quantity
    summary.available_quantity += payload.quantity

    # 4. Log transaction
    tx = StockTransaction(
        user_id=user_id,
        branch_id=payload.branch_id,
        batch_id=batch.id,
        quantity_changed=payload.quantity,
        transaction_type="Stock In",
        reason=payload.reason or "Stock received",
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx

async def perform_dispense(
    db: AsyncSession, payload: DispensePayload, current_user: User
) -> StockTransaction:
    # 1. Fetch batch with summary
    batch = await get_batch_by_id(db, payload.batch_id)
    if not batch or not batch.summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory batch not found")

    summary = batch.summary

    # 2. Server-side Branch Boundary Verification
    if current_user.role == "assistant":
        if str(summary.branch_id) != str(current_user.default_branch_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot dispense stock belonging to another branch."
            )

    # 3. Expiry Check
    if batch.expiry_date and batch.expiry_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot dispense expired medicine. Batch has expired.",
        )

    # 4. Atomic Stock Deduction (Prevents race conditions & negative stock)
    stmt = (
        update(InventoryBatch)
        .where(
            InventoryBatch.id == payload.batch_id,
            InventoryBatch.quantity >= payload.quantity
        )
        .values(quantity=InventoryBatch.quantity - payload.quantity)
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock in batch. Available quantity is less than requested {payload.quantity}.",
        )

    # 5. Atomic Summary Deduction
    summary_stmt = (
        update(InventorySummary)
        .where(
            InventorySummary.id == summary.id,
            InventorySummary.available_quantity >= payload.quantity
        )
        .values(
            total_quantity=InventorySummary.total_quantity - payload.quantity,
            available_quantity=InventorySummary.available_quantity - payload.quantity
        )
    )
    await db.execute(summary_stmt)

    # 6. Log transaction
    tx = StockTransaction(
        user_id=current_user.id,
        branch_id=summary.branch_id,
        batch_id=batch.id,
        quantity_changed=-payload.quantity,
        transaction_type="Dispense",
        reason=payload.reason or "Dispensed to patient",
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx

async def perform_transfer(
    db: AsyncSession, payload: TransferPayload, current_user: User
) -> Tuple[StockTransaction, StockTransaction]:
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Stock transfers can only be performed by doctors."
        )

    # 1. Fetch source batch
    source_batch = await get_batch_by_id(db, payload.batch_id)
    if not source_batch or not source_batch.summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source batch not found")

    source_summary = source_batch.summary
    if str(source_summary.branch_id) == str(payload.to_branch_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination branches cannot be the same.",
        )

    # 2. Atomic deduction from source batch (Rolls back entire transaction on conflict)
    stmt_deduct = (
        update(InventoryBatch)
        .where(
            InventoryBatch.id == source_batch.id,
            InventoryBatch.quantity >= payload.quantity
        )
        .values(quantity=InventoryBatch.quantity - payload.quantity)
    )
    res = await db.execute(stmt_deduct)
    if res.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock in source batch for transfer. Requested: {payload.quantity}",
        )

    # Deduct from source summary
    await db.execute(
        update(InventorySummary)
        .where(InventorySummary.id == source_summary.id)
        .values(
            total_quantity=InventorySummary.total_quantity - payload.quantity,
            available_quantity=InventorySummary.available_quantity - payload.quantity,
        )
    )

    # 3. Log Transfer Out
    tx_out = StockTransaction(
        user_id=current_user.id,
        branch_id=source_summary.branch_id,
        batch_id=source_batch.id,
        quantity_changed=-payload.quantity,
        transaction_type="Transfer Out",
        reason=payload.reason or f"Transfer to branch {payload.to_branch_id}",
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
            cupboard=source_batch.cupboard,
            rack=source_batch.rack,
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
            quantity=payload.quantity,
            cupboard=source_batch.cupboard,
            rack=source_batch.rack,
            row=source_batch.row,
            column=source_batch.column,
        )
        db.add(dest_batch)
        await db.flush()
    else:
        dest_batch.quantity += payload.quantity

    dest_summary.total_quantity += payload.quantity
    dest_summary.available_quantity += payload.quantity

    # 6. Log Transfer In
    tx_in = StockTransaction(
        user_id=current_user.id,
        branch_id=payload.to_branch_id,
        batch_id=dest_batch.id,
        quantity_changed=payload.quantity,
        transaction_type="Transfer In",
        reason=payload.reason or f"Transfer from branch {source_summary.branch_id}",
    )
    db.add(tx_in)

    # 7. Single atomic commit for both sides of transfer
    await db.commit()
    await db.refresh(tx_out)
    await db.refresh(tx_in)
    return tx_out, tx_in

async def perform_adjustment(
    db: AsyncSession, payload: AdjustmentPayload, current_user: User
) -> StockTransaction:
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Stock adjustments can only be performed by doctors."
        )

    batch = await get_batch_by_id(db, payload.batch_id)
    if not batch or not batch.summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory batch not found")

    summary = batch.summary

    # Atomic update preventing negative stock
    if payload.quantity_changed < 0:
        stmt = (
            update(InventoryBatch)
            .where(
                InventoryBatch.id == batch.id,
                InventoryBatch.quantity >= abs(payload.quantity_changed)
            )
            .values(quantity=InventoryBatch.quantity + payload.quantity_changed)
        )
        res = await db.execute(stmt)
        if res.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Adjustment results in negative stock. Current quantity is {batch.quantity}.",
            )
    else:
        await db.execute(
            update(InventoryBatch)
            .where(InventoryBatch.id == batch.id)
            .values(quantity=InventoryBatch.quantity + payload.quantity_changed)
        )

    await db.execute(
        update(InventorySummary)
        .where(InventorySummary.id == summary.id)
        .values(
            total_quantity=InventorySummary.total_quantity + payload.quantity_changed,
            available_quantity=InventorySummary.available_quantity + payload.quantity_changed,
        )
    )

    tx = StockTransaction(
        user_id=current_user.id,
        branch_id=summary.branch_id,
        batch_id=batch.id,
        quantity_changed=payload.quantity_changed,
        transaction_type=payload.transaction_type,
        reason=payload.reason or "Inventory adjustment",
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx
