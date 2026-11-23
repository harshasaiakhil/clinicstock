from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, case
from uuid import UUID
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional

from app.models.medicine import Medicine
from app.models.inventory import InventorySummary, InventoryBatch, StockTransaction
from app.models.branch import Branch
from app.crud import inventory as crud_inventory

async def get_dashboard_analytics(
    db: AsyncSession, branch_id: Optional[UUID] = None
) -> Dict[str, Any]:
    # 1. Total Medicines (catalog counts)
    total_meds = await db.scalar(
        select(func.count(Medicine.id)).where(Medicine.is_deleted == False)
    ) or 0
    total_active_meds = await db.scalar(
        select(func.count(Medicine.id)).where(
            Medicine.is_deleted == False, Medicine.is_active == True
        )
    ) or 0

    # 2. Combined Inventory Summary Aggregates (Items, Low Stock, Out of Stock in a single SQL query)
    inv_summary_query = select(
        func.coalesce(func.sum(InventorySummary.available_quantity), 0).label("total_items"),
        func.coalesce(func.sum(
            case((InventorySummary.available_quantity <= InventorySummary.reorder_level, 1), else_=0)
        ), 0).label("low_stock_count"),
        func.coalesce(func.sum(
            case((InventorySummary.available_quantity == 0, 1), else_=0)
        ), 0).label("out_of_stock_count"),
    )
    if branch_id:
        inv_summary_query = inv_summary_query.where(InventorySummary.branch_id == branch_id)
    inv_row = (await db.execute(inv_summary_query)).first()
    total_inv_items = int(inv_row.total_items) if inv_row else 0
    low_stock_count = int(inv_row.low_stock_count) if inv_row else 0
    out_of_stock_count = int(inv_row.out_of_stock_count) if inv_row else 0

    # 3. Total Inventory Valuation
    val_query = select(
        func.coalesce(func.sum(InventoryBatch.quantity * InventoryBatch.purchase_price), 0.0)
    ).join(InventoryBatch.summary)
    if branch_id:
        val_query = val_query.where(InventorySummary.branch_id == branch_id)
    total_inv_value = await db.scalar(val_query) or 0.0

    # 4. Combined Expiry Aggregates (Expiring in 30 days & Expired in a single SQL query)
    exp_query = (
        select(
            func.coalesce(func.sum(
                case(
                    (
                        (InventoryBatch.quantity > 0) &
                        (InventoryBatch.expiry_date >= date.today()) &
                        (InventoryBatch.expiry_date <= date.today() + timedelta(days=30)),
                        1
                    ),
                    else_=0
                )
            ), 0).label("expiring_30"),
            func.coalesce(func.sum(
                case(
                    (
                        (InventoryBatch.quantity > 0) &
                        (InventoryBatch.expiry_date < date.today()),
                        1
                    ),
                    else_=0
                )
            ), 0).label("expired"),
        )
        .join(InventoryBatch.summary)
    )
    if branch_id:
        exp_query = exp_query.where(InventorySummary.branch_id == branch_id)
    exp_row = (await db.execute(exp_query)).first()
    expiring_30_days = int(exp_row.expiring_30) if exp_row else 0
    expired_count = int(exp_row.expired) if exp_row else 0

    # 5. Combined Today's Transaction Quantities (Single SQL aggregation replaces 5 separate queries)
    today_start = datetime.combine(date.today(), datetime.min.time())
    tx_agg_query = (
        select(
            func.coalesce(func.sum(
                case((StockTransaction.transaction_type == "Stock In", StockTransaction.quantity_changed), else_=0)
            ), 0).label("stock_in"),
            func.coalesce(func.sum(
                case((StockTransaction.transaction_type == "Dispense", StockTransaction.quantity_changed), else_=0)
            ), 0).label("dispensed"),
            func.coalesce(func.sum(
                case((StockTransaction.transaction_type == "Transfer In", StockTransaction.quantity_changed), else_=0)
            ), 0).label("transfers"),
            func.coalesce(func.sum(
                case((StockTransaction.transaction_type == "Adjustment", StockTransaction.quantity_changed), else_=0)
            ), 0).label("adjustments"),
            func.coalesce(func.sum(
                case((StockTransaction.transaction_type.in_(["Damaged", "Expired"]), StockTransaction.quantity_changed), else_=0)
            ), 0).label("damaged"),
        )
        .where(StockTransaction.timestamp >= today_start)
    )
    if branch_id:
        tx_agg_query = tx_agg_query.where(StockTransaction.branch_id == branch_id)
    tx_row = (await db.execute(tx_agg_query)).first()
    todays_stock_in = int(tx_row.stock_in) if tx_row else 0
    todays_dispensed = abs(int(tx_row.dispensed)) if tx_row else 0
    todays_transfers = int(tx_row.transfers) if tx_row else 0
    todays_adjustments = int(tx_row.adjustments) if tx_row else 0
    todays_damaged = abs(int(tx_row.damaged)) if tx_row else 0

    # 6. Branch-wise breakdown (Only needed for global/all-branches view)
    branch_stats = []
    if not branch_id:
        summary_sub = (
            select(
                InventorySummary.branch_id,
                func.coalesce(func.sum(InventorySummary.available_quantity), 0).label("total_items"),
                func.coalesce(func.sum(
                    case((InventorySummary.available_quantity <= InventorySummary.reorder_level, 1), else_=0)
                ), 0).label("low_stock_count"),
            )
            .group_by(InventorySummary.branch_id)
            .subquery()
        )

        batch_sub = (
            select(
                InventorySummary.branch_id,
                func.coalesce(func.sum(InventoryBatch.quantity * InventoryBatch.purchase_price), 0.0).label("total_val")
            )
            .join(InventoryBatch, InventoryBatch.inventory_summary_id == InventorySummary.id)
            .group_by(InventorySummary.branch_id)
            .subquery()
        )

        branch_query = (
            select(
                Branch.id,
                Branch.name,
                Branch.code,
                func.coalesce(summary_sub.c.total_items, 0).label("total_items"),
                func.coalesce(batch_sub.c.total_val, 0.0).label("total_val"),
                func.coalesce(summary_sub.c.low_stock_count, 0).label("low_stock_count"),
            )
            .outerjoin(summary_sub, summary_sub.c.branch_id == Branch.id)
            .outerjoin(batch_sub, batch_sub.c.branch_id == Branch.id)
            .where(Branch.is_active == True)
            .order_by(Branch.name)
        )

        b_res = await db.execute(branch_query)
        for r in b_res.all():
            branch_stats.append({
                "branch_id": r.id,
                "branch_name": r.name,
                "branch_code": r.code,
                "total_inventory_items": int(r.total_items),
                "total_inventory_value": float(r.total_val),
                "low_stock_count": int(r.low_stock_count),
            })

    # 7. Top 10 Frequently Dispensed Medicines
    top_disp_query = (
        select(
            Medicine.id.label("medicine_id"),
            Medicine.name,
            Medicine.generic_name,
            func.abs(func.sum(StockTransaction.quantity_changed)).label("total_dispensed"),
        )
        .join(InventoryBatch, StockTransaction.batch_id == InventoryBatch.id)
        .join(InventorySummary, InventoryBatch.inventory_summary_id == InventorySummary.id)
        .join(Medicine, InventorySummary.medicine_id == Medicine.id)
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

    # 8. Top 10 Low Stock Medicines
    top_low_query = (
        select(
            Medicine.id.label("medicine_id"),
            Medicine.name,
            Medicine.generic_name,
            InventorySummary.available_quantity,
        )
        .join(Medicine, InventorySummary.medicine_id == Medicine.id)
        .where(
            Medicine.is_deleted == False,
            InventorySummary.available_quantity <= InventorySummary.reorder_level
        )
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

    # 9. Recent Activity (Recent 10 transactions)
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
