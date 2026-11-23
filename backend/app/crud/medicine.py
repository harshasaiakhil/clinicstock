from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional, Tuple
import math

from app.models.medicine import Medicine, Category, Manufacturer, MedicineUnit, Potency
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

def _build_medicines_query(
    search: Optional[str] = None,
    category_id: Optional[UUID] = None,
    manufacturer_id: Optional[UUID] = None,
    potency_id: Optional[UUID] = None,
    unit_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
):
    query = select(Medicine).where(Medicine.is_deleted == False)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.outerjoin(Medicine.category)\
                     .outerjoin(Medicine.manufacturer)\
                     .outerjoin(Medicine.potency)\
                     .outerjoin(Medicine.unit)
        query = query.where(
            (Medicine.name.ilike(search_term)) |
            (Medicine.generic_name.ilike(search_term)) |
            (Medicine.hsn_code.ilike(search_term)) |
            (Medicine.barcode.ilike(search_term)) |
            (Medicine.qr_code.ilike(search_term)) |
            (Category.name.ilike(search_term)) |
            (Manufacturer.name.ilike(search_term)) |
            (Potency.name.ilike(search_term)) |
            (MedicineUnit.name.ilike(search_term)) |
            (MedicineUnit.code.ilike(search_term))
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

    return query

async def get_medicines_paginated(
    db: AsyncSession,
    search: Optional[str] = None,
    category_id: Optional[UUID] = None,
    manufacturer_id: Optional[UUID] = None,
    potency_id: Optional[UUID] = None,
    unit_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[Medicine], int, int]:
    # Enforce bounds
    page = max(1, page)
    page_size = min(100, max(1, page_size))

    # Base query
    base_query = _build_medicines_query(
        search=search,
        category_id=category_id,
        manufacturer_id=manufacturer_id,
        potency_id=potency_id,
        unit_id=unit_id,
        is_active=is_active,
    )

    # 1. Total count executed in DB
    count_query = select(func.count()).select_from(base_query.subquery())
    total = await db.scalar(count_query) or 0

    # 2. Sorting
    valid_sort_fields = {
        "name": Medicine.name,
        "selling_price": Medicine.selling_price,
        "quantity": Medicine.quantity,
        "created_at": Medicine.created_at,
        "updated_at": Medicine.updated_at,
    }
    sort_col = valid_sort_fields.get(sort_by, Medicine.name)
    if sort_order.lower() == "desc":
        sort_expr = sort_col.desc()
    else:
        sort_expr = sort_col.asc()

    # 3. Pagination & selective eager loading (shallow relations only, NO heavy nested batch trees)
    offset = (page - 1) * page_size
    items_query = (
        base_query
        .order_by(sort_expr)
        .offset(offset)
        .limit(page_size)
        .options(
            selectinload(Medicine.category),
            selectinload(Medicine.manufacturer),
            selectinload(Medicine.potency),
            selectinload(Medicine.unit),
        )
    )

    result = await db.execute(items_query)
    items = list(result.scalars().all())

    pages = math.ceil(total / page_size) if total > 0 else 1
    return items, total, pages

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
    query = _build_medicines_query(
        search=search,
        category_id=category_id,
        manufacturer_id=manufacturer_id,
        potency_id=potency_id,
        unit_id=unit_id,
        is_active=is_active,
    )

    valid_sort_fields = {
        "name": Medicine.name,
        "selling_price": Medicine.selling_price,
        "quantity": Medicine.quantity,
        "created_at": Medicine.created_at,
        "updated_at": Medicine.updated_at,
    }
    sort_col = valid_sort_fields.get(sort_by or "name", Medicine.name)
    if (sort_order or "asc").lower() == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    query = query.offset(skip).limit(min(100, limit)).options(
        selectinload(Medicine.category),
        selectinload(Medicine.manufacturer),
        selectinload(Medicine.potency),
        selectinload(Medicine.unit),
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
