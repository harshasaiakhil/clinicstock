from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List, Optional
from app.models.purchase_order import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate

async def get_supplier(db: AsyncSession, supplier_id: UUID) -> Optional[Supplier]:
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.is_active == True))
    return result.scalars().first()

async def get_supplier_by_name(db: AsyncSession, name: str) -> Optional[Supplier]:
    result = await db.execute(select(Supplier).where(Supplier.name == name, Supplier.is_active == True))
    return result.scalars().first()

async def get_suppliers(
    db: AsyncSession, search: Optional[str] = None, skip: int = 0, limit: int = 100
) -> List[Supplier]:
    query = select(Supplier).where(Supplier.is_active == True)
    if search:
        query = query.where(Supplier.name.ilike(f"%{search}%"))
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())

async def create_supplier(db: AsyncSession, supplier: SupplierCreate) -> Supplier:
    db_supplier = Supplier(
        name=supplier.name,
        contact_name=supplier.contact_name,
        email=supplier.email,
        phone=supplier.phone,
        address=supplier.address,
        is_active=supplier.is_active
    )
    db.add(db_supplier)
    await db.commit()
    await db.refresh(db_supplier)
    return db_supplier

async def update_supplier(db: AsyncSession, supplier_id: UUID, supplier_update: SupplierUpdate) -> Optional[Supplier]:
    db_supplier = await get_supplier(db, supplier_id)
    if not db_supplier:
        return None
    update_data = supplier_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_supplier, key, value)
    await db.commit()
    await db.refresh(db_supplier)
    return db_supplier

async def delete_supplier(db: AsyncSession, supplier_id: UUID) -> bool:
    db_supplier = await get_supplier(db, supplier_id)
    if not db_supplier:
        return False
    db_supplier.is_active = False
    await db.commit()
    return True
