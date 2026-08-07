from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

from app.models.medicine import Medicine
from app.models.inventory import InventorySummary, InventoryBatch, StockTransaction
from app.models.branch import Branch
from app.crud import inventory as crud_inventory

async def get_dashboard_analytics(
    db: AsyncSession, branch_id: Optional[UUID] = None
) -> Dict[str, Any]:
    # 1. Total Medicines (catalog counts are global, but inventory counts can filter by branch)
    total_meds = await db.scalar(
        select(func.count(Medicine.id)).where(Medicine.is_deleted == False)
    )
    total_active_meds = await db.scalar(
        select(func.count(Medicine.id)).where(
            Medicine.is_deleted == False, Medicine.is_active == True
        )
    )

    # 2. Total Inventory Items (available quantities)
    items_query = select(func.coalesce(func.sum(InventorySummary.available_quantity), 0))
    if branch_id:
        items_query = items_query.where(InventorySummary.branch_id == branch_id)
    total_inv_items = await db.scalar(items_query)

    # 3. Total Inventory Value
    val_query = select(
        func.coalesce(func.sum(InventoryBatch.quantity * InventoryBatch.purchase_price), 0.0)
    ).join(InventoryBatch.summary)
    if branch_id:
        val_query = val_query.where(InventorySummary.branch_id == branch_id)
    total_inv_value = await db.scalar(val_query)

    # 4. Low Stock Count (available_quantity <= reorder_level)
    low_query = select(func.count(InventorySummary.id)).where(
        InventorySummary.available_quantity <= InventorySummary.reorder_level
    )
    if branch_id:
        low_query = low_query.where(InventorySummary.branch_id == branch_id)
    low_stock_count = await db.scalar(low_query)

    # 5. Out of Stock Count (available_quantity == 0)
    oos_query = select(func.count(InventorySummary.id)).where(
        InventorySummary.available_quantity == 0
    )
    if branch_id:
        oos_query = oos_query.where(InventorySummary.branch_id == branch_id)
    out_of_stock_count = await db.scalar(oos_query)

    # 6. Expiry tracking counts
    exp_30_query = (
        select(func.count(InventoryBatch.id))
        .join(InventoryBatch.summary)
        .where(
            InventoryBatch.quantity > 0,
            InventoryBatch.expiry_date >= date.today(),
            InventoryBatch.expiry_date <= date.today() + timedelta(days=30),
        )
    )
    if branch_id:
        exp_30_query = exp_30_query.where(InventorySummary.branch_id == branch_id)
    expiring_30_days = await db.scalar(exp_30_query)

    expired_query = (
        select(func.count(InventoryBatch.id))
        .join(InventoryBatch.summary)
        .where(InventoryBatch.quantity > 0, InventoryBatch.expiry_date < date.today())
    )
    if branch_id:
        expired_query = expired_query.where(InventorySummary.branch_id == branch_id)
    expired_count = await db.scalar(expired_query)

    # 7. Today's transaction quantities (since local time timezone might differ, we fetch from start of today UTC/local)
    today_start = datetime.combine(date.today(), datetime.min.time())

    # Today's Stock In
    sin_query = select(func.coalesce(func.sum(StockTransaction.quantity_changed), 0)).where(
        StockTransaction.transaction_type == "Stock In",
        StockTransaction.timestamp >= today_start,
    )
    if branch_id:
        sin_query = sin_query.where(StockTransaction.branch_id == branch_id)
    todays_stock_in = await db.scalar(sin_query)

    # Today's Dispensed (Dispense changes are negative, we take absolute value)
    disp_query = select(func.coalesce(func.sum(StockTransaction.quantity_changed), 0)).where(
        StockTransaction.transaction_type == "Dispense",
        StockTransaction.timestamp >= today_start,
    )
    if branch_id:
        disp_query = disp_query.where(StockTransaction.branch_id == branch_id)
    todays_dispensed = abs(await db.scalar(disp_query))

    # Today's Transfers (Sum of Transfer In quantities)
    trans_query = select(func.coalesce(func.sum(StockTransaction.quantity_changed), 0)).where(
        StockTransaction.transaction_type == "Transfer In",
        StockTransaction.timestamp >= today_start,
    )
    if branch_id:
        trans_query = trans_query.where(StockTransaction.branch_id == branch_id)
    todays_transfers = await db.scalar(trans_query)

    # Today's Adjustments (Sum of Adjustment type changes, excluding Expired/Damaged)
    adj_query = select(func.coalesce(func.sum(StockTransaction.quantity_changed), 0)).where(
        StockTransaction.transaction_type == "Adjustment",
        StockTransaction.timestamp >= today_start,
    )
    if branch_id:
        adj_query = adj_query.where(StockTransaction.branch_id == branch_id)
    todays_adjustments = await db.scalar(adj_query)

    # Today's Damaged (Sum of Damaged or Expired changes)
    dmg_query = select(func.coalesce(func.sum(StockTransaction.quantity_changed), 0)).where(
        StockTransaction.transaction_type.in_(["Damaged", "Expired"]),
        StockTransaction.timestamp >= today_start,
    )
    if branch_id:
        dmg_query = dmg_query.where(StockTransaction.branch_id == branch_id)
    todays_damaged = abs(await db.scalar(dmg_query))

    # 8. Branch-wise breakdown (only returned system-wide, i.e., branch_id is None)
    branch_stats = []
    if not branch_id:
        branches_res = await db.execute(select(Branch))
        branches = branches_res.scalars().all()
        for b in branches:
            inv_items = await db.scalar(
                select(func.coalesce(func.sum(InventorySummary.available_quantity), 0)).where(
                    InventorySummary.branch_id == b.id
                )
            )
            inv_val = await db.scalar(
                select(
                    func.coalesce(
                        func.sum(InventoryBatch.quantity * InventoryBatch.purchase_price), 0.0
                    )
                )
                .join(InventoryBatch.summary)
                .where(InventorySummary.branch_id == b.id)
            )
            low_stock = await db.scalar(
                select(func.count(InventorySummary.id)).where(
                    InventorySummary.branch_id == b.id,
                    InventorySummary.available_quantity <= InventorySummary.reorder_level,
                )
            )
            branch_stats.append(
                {
                    "branch_id": b.id,
                    "branch_name": b.name,
                    "branch_code": b.code,
                    "total_inventory_items": inv_items,
                    "total_inventory_value": float(inv_val),
                    "low_stock_count": low_stock,
                }
            )

    # 9. Top 10 Frequently Dispensed Medicines (highest Dispense quantities)
    top_disp_query = (
        select(
            Medicine.id.label("medicine_id"),
            Medicine.name,
            Medicine.generic_name,
            func.abs(func.sum(StockTransaction.quantity_changed)).label("total_dispensed"),
        )
        .join(InventorySummary, InventorySummary.medicine_id == Medicine.id)
        .join(InventoryBatch, InventoryBatch.inventory_summary_id == InventorySummary.id)
        .join(StockTransaction, StockTransaction.batch_id == InventoryBatch.id)
        .where(StockTransaction.transaction_type == "Dispense")
    )
    if branch_id:
        top_disp_query = top_disp_query.where(StockTransaction.branch_id == branch_id)

    top_disp_query = (
        top_disp_query.group_by(Medicine.id, Medicine.name, Medicine.generic_name)
        .order_by(func.abs(func.sum(StockTransaction.quantity_changed)).desc())
        .limit(10)
    )
    top_disp_res = await db.execute(top_disp_query)
    top_dispensed = [
        {
            "medicine_id": r.medicine_id,
            "name": r.name,
            "generic_name": r.generic_name,
            "value": int(r.total_dispensed),
        }
        for r in top_disp_res.all()
    ]

    # 10. Top 10 Low Stock Medicines (sorted by available stock ascending)
    top_low_query = (
        select(
            Medicine.id.label("medicine_id"),
            Medicine.name,
            Medicine.generic_name,
            InventorySummary.available_quantity,
        )
        .join(InventorySummary, InventorySummary.medicine_id == Medicine.id)
        .where(InventorySummary.available_quantity <= InventorySummary.reorder_level)
    )
    if branch_id:
        top_low_query = top_low_query.where(InventorySummary.branch_id == branch_id)

    top_low_query = top_low_query.order_by(InventorySummary.available_quantity.asc()).limit(10)
    top_low_res = await db.execute(top_low_query)
    top_low_stock = [
        {
            "medicine_id": r.medicine_id,
            "name": r.name,
            "generic_name": r.generic_name,
            "value": r.available_quantity,
        }
        for r in top_low_res.all()
    ]

    # 11. Recent Activity Timeline (recent 10 transactions)
    recent_txs = await crud_inventory.get_transactions(db, branch_id=branch_id, limit=10)

    return {
        "total_medicines": total_meds,
        "total_active_medicines": total_active_meds,
        "total_inventory_items": total_inv_items,
        "total_inventory_value": float(total_inv_value),
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "expiring_30_days_count": expiring_30_days,
        "expired_count": expired_count,
        "todays_stock_in": todays_stock_in,
        "todays_dispensed": todays_dispensed,
        "todays_transfers": todays_transfers,
        "todays_adjustments": todays_adjustments,
        "todays_damaged": todays_damaged,
        "branch_wise_stats": branch_stats,
        "top_dispensed_medicines": top_dispensed,
        "top_low_stock_medicines": top_low_stock,
        "recent_activity": recent_txs,
    }
