from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import date
from typing import List, Optional

from app.models.inventory import InventorySummary, InventoryBatch, StockTransaction
from app.models.medicine import Medicine
from app.schemas.inventory import InventorySummaryUpdate, InventoryBatchUpdate

async def get_inventory_summary(db: AsyncSession, summary_id: UUID) -> Optional[InventorySummary]:
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

async def get_inventory_summaries(
    db: AsyncSession,
    search: Optional[str] = None,
    branch_id: Optional[UUID] = None,
    is_low_stock: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[InventorySummary]:
    query = select(InventorySummary)

    # Join Medicine to support search
    if search:
        query = query.join(InventorySummary.medicine).where(
            (Medicine.name.ilike(f"%{search}%")) | (Medicine.generic_name.ilike(f"%{search}%"))
        )

    if branch_id:
        query = query.where(InventorySummary.branch_id == branch_id)

    if is_low_stock is not None:
        if is_low_stock:
            query = query.where(InventorySummary.available_quantity <= InventorySummary.reorder_level)
        else:
            query = query.where(InventorySummary.available_quantity > InventorySummary.reorder_level)

    query = query.offset(skip).limit(limit).options(
        selectinload(InventorySummary.medicine),
        selectinload(InventorySummary.branch),
        selectinload(InventorySummary.batches),
    )
    result = await db.execute(query)
    return list(result.scalars().all())

async def update_inventory_summary(
    db: AsyncSession, summary_id: UUID, summary_update: InventorySummaryUpdate
) -> Optional[InventorySummary]:
    db_summary = await get_inventory_summary(db, summary_id)
    if not db_summary:
        return None
    update_data = summary_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_summary, key, value)
    await db.commit()
    await db.refresh(db_summary)
    return db_summary

async def get_inventory_batch(db: AsyncSession, batch_id: UUID) -> Optional[InventoryBatch]:
    result = await db.execute(
        select(InventoryBatch)
        .where(InventoryBatch.id == batch_id)
        .options(
            selectinload(InventoryBatch.summary).selectinload(InventorySummary.medicine),
            selectinload(InventoryBatch.summary).selectinload(InventorySummary.branch),
            selectinload(InventoryBatch.supplier),
        )
    )
    return result.scalars().first()

async def get_inventory_batches(
    db: AsyncSession,
    summary_id: Optional[UUID] = None,
    branch_id: Optional[UUID] = None,
    is_expired: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[InventoryBatch]:
    query = select(InventoryBatch)
    if summary_id:
        query = query.where(InventoryBatch.inventory_summary_id == summary_id)
    if branch_id:
        query = query.join(InventoryBatch.summary).where(InventorySummary.branch_id == branch_id)

    if is_expired is not None:
        if is_expired:
            query = query.where(
                InventoryBatch.expiry_date != None, InventoryBatch.expiry_date < date.today()
            )
        else:
            query = query.where(
                (InventoryBatch.expiry_date == None) | (InventoryBatch.expiry_date >= date.today())
            )

    query = query.offset(skip).limit(limit).options(
        selectinload(InventoryBatch.summary).selectinload(InventorySummary.medicine),
        selectinload(InventoryBatch.summary).selectinload(InventorySummary.branch),
        selectinload(InventoryBatch.supplier),
    )
    result = await db.execute(query)
    return list(result.scalars().all())

async def update_inventory_batch(
    db: AsyncSession, batch_id: UUID, batch_update: InventoryBatchUpdate
) -> Optional[InventoryBatch]:
    db_batch = await get_inventory_batch(db, batch_id)
    if not db_batch:
        return None
    update_data = batch_update.model_dump(exclude_unset=True)

    qty_diff = 0
    if "quantity" in update_data and update_data["quantity"] is not None:
        qty_diff = update_data["quantity"] - db_batch.quantity

    for key, value in update_data.items():
        setattr(db_batch, key, value)

    await db.commit()
    await db.refresh(db_batch)

    if qty_diff != 0:
        summary = db_batch.summary
        if summary:
            summary.total_quantity += qty_diff
            summary.available_quantity += qty_diff
            db.add(summary)
            await db.commit()
            await db.refresh(db_batch)

    return db_batch

async def get_transactions(
    db: AsyncSession,
    branch_id: Optional[UUID] = None,
    transaction_type: Optional[str] = None,
    batch_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[StockTransaction]:
    query = select(StockTransaction)
    if branch_id:
        query = query.where(StockTransaction.branch_id == branch_id)
    if transaction_type:
        query = query.where(StockTransaction.transaction_type == transaction_type)
    if batch_id:
        query = query.where(StockTransaction.batch_id == batch_id)

    query = query.order_by(StockTransaction.timestamp.desc()).offset(skip).limit(limit).options(
        selectinload(StockTransaction.branch),
        selectinload(StockTransaction.batch).selectinload(InventoryBatch.summary).selectinload(InventorySummary.medicine),
        selectinload(StockTransaction.user),
    )
    result = await db.execute(query)
    return list(result.scalars().all())

async def get_transaction_with_details(db: AsyncSession, tx_id: UUID) -> Optional[StockTransaction]:
    result = await db.execute(
        select(StockTransaction)
        .where(StockTransaction.id == tx_id)
        .options(
            selectinload(StockTransaction.branch),
            selectinload(StockTransaction.batch).selectinload(InventoryBatch.summary).selectinload(InventorySummary.medicine),
            selectinload(StockTransaction.batch).selectinload(InventoryBatch.summary).selectinload(InventorySummary.branch),
            selectinload(StockTransaction.batch).selectinload(InventoryBatch.supplier),
            selectinload(StockTransaction.user),
        )
    )
    return result.scalars().first()
