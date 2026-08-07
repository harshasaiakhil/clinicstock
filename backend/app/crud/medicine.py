from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional
from app.models.medicine import Medicine
from app.schemas.medicine import MedicineCreate, MedicineUpdate

async def get_medicine(db: AsyncSession, medicine_id: UUID) -> Optional[Medicine]:
    result = await db.execute(
        select(Medicine)
        .where(Medicine.id == medicine_id, Medicine.is_deleted == False)
        .options(
            selectinload(Medicine.category),
            selectinload(Medicine.manufacturer),
            selectinload(Medicine.potency),
            selectinload(Medicine.unit),
        )
    )
    return result.scalars().first()

async def get_medicine_by_unique_key(
    db: AsyncSession, name: str, manufacturer_id: Optional[UUID], potency_id: UUID
) -> Optional[Medicine]:
    result = await db.execute(
        select(Medicine)
        .where(
            Medicine.name == name,
            Medicine.manufacturer_id == manufacturer_id,
            Medicine.potency_id == potency_id,
            Medicine.is_deleted == False,
        )
        .options(
            selectinload(Medicine.category),
            selectinload(Medicine.manufacturer),
            selectinload(Medicine.potency),
            selectinload(Medicine.unit),
        )
    )
    return result.scalars().first()

async def get_medicines(
    db: AsyncSession,
    search: Optional[str] = None,
    category_id: Optional[UUID] = None,
    manufacturer_id: Optional[UUID] = None,
    potency_id: Optional[UUID] = None,
    unit_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    sort_by: Optional[str] = "name",
    sort_order: Optional[str] = "asc",
    skip: int = 0,
    limit: int = 100,
) -> List[Medicine]:
    query = select(Medicine).where(Medicine.is_deleted == False)

    # Filtering
    if search:
        from app.models.medicine import Category, Manufacturer, MedicineUnit, Potency
        query = query.outerjoin(Medicine.category)\
                     .outerjoin(Medicine.manufacturer)\
                     .outerjoin(Medicine.potency)\
                     .outerjoin(Medicine.unit)
        query = query.where(
            (Medicine.name.ilike(f"%{search}%")) |
            (Medicine.generic_name.ilike(f"%{search}%")) |
            (Medicine.hsn_code.ilike(f"%{search}%")) |
            (Medicine.barcode.ilike(f"%{search}%")) |
            (Medicine.qr_code.ilike(f"%{search}%")) |
            (Category.name.ilike(f"%{search}%")) |
            (Manufacturer.name.ilike(f"%{search}%")) |
            (Potency.name.ilike(f"%{search}%")) |
            (MedicineUnit.name.ilike(f"%{search}%")) |
            (MedicineUnit.code.ilike(f"%{search}%"))
        )
    if category_id:
        query = query.where(Medicine.category_id == category_id)
    if manufacturer_id:
        query = query.where(Medicine.manufacturer_id == manufacturer_id)
    if potency_id:
        query = query.where(Medicine.potency_id == potency_id)
    if unit_id:
        query = query.where(Medicine.unit_id == unit_id)
    if is_active is not None:
        query = query.where(Medicine.is_active == is_active)

    # Sorting
    sort_column = getattr(Medicine, sort_by, Medicine.name)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    from app.models.inventory import InventorySummary
    query = query.offset(skip).limit(limit).options(
        selectinload(Medicine.category),
        selectinload(Medicine.manufacturer),
        selectinload(Medicine.potency),
        selectinload(Medicine.unit),
        selectinload(Medicine.inventories).selectinload(InventorySummary.branch),
        selectinload(Medicine.inventories).selectinload(InventorySummary.batches),
    )
    result = await db.execute(query)
    return list(result.scalars().all())

async def create_medicine(db: AsyncSession, medicine: MedicineCreate, user_id: UUID) -> Medicine:
    db_medicine = Medicine(
        name=medicine.name,
        generic_name=medicine.generic_name,
        category_id=medicine.category_id,
        manufacturer_id=medicine.manufacturer_id,
        potency_id=medicine.potency_id,
        unit_id=medicine.unit_id,
        quantity=medicine.quantity,
        selling_price=medicine.selling_price,
        gst_percentage=medicine.gst_percentage,
        hsn_code=medicine.hsn_code,
        description=medicine.description,
        image_url=medicine.image_url,
        barcode=medicine.barcode,
        qr_code=medicine.qr_code,
        is_active=medicine.is_active,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(db_medicine)
    await db.commit()
    await db.refresh(db_medicine)
    return await get_medicine(db, db_medicine.id)

async def update_medicine(
    db: AsyncSession, medicine_id: UUID, medicine_update: MedicineUpdate, user_id: UUID
) -> Optional[Medicine]:
    db_medicine = await get_medicine(db, medicine_id)
    if not db_medicine:
        return None

    update_data = medicine_update.model_dump(exclude_unset=True)
    update_data["updated_by"] = user_id
    update_data["updated_at"] = func.now()

    for key, value in update_data.items():
        setattr(db_medicine, key, value)

    await db.commit()
    await db.refresh(db_medicine)
    return await get_medicine(db, db_medicine.id)

async def set_medicine_active_status(
    db: AsyncSession, medicine_id: UUID, is_active: bool, user_id: UUID
) -> Optional[Medicine]:
    db_medicine = await get_medicine(db, medicine_id)
    if not db_medicine:
        return None
    db_medicine.is_active = is_active
    db_medicine.updated_by = user_id
    db_medicine.updated_at = func.now()
    await db.commit()
    await db.refresh(db_medicine)
    return db_medicine
