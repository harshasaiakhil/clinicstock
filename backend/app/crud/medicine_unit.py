from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List, Optional
from app.models.medicine import MedicineUnit
from app.schemas.medicine_unit import MedicineUnitCreate, MedicineUnitUpdate

async def get_medicine_unit(db: AsyncSession, unit_id: UUID) -> Optional[MedicineUnit]:
    result = await db.execute(select(MedicineUnit).where(MedicineUnit.id == unit_id, MedicineUnit.is_deleted == False))
    return result.scalars().first()

async def get_medicine_unit_by_code(db: AsyncSession, code: str) -> Optional[MedicineUnit]:
    result = await db.execute(select(MedicineUnit).where(MedicineUnit.code == code, MedicineUnit.is_deleted == False))
    return result.scalars().first()

async def get_medicine_unit_by_name(db: AsyncSession, name: str) -> Optional[MedicineUnit]:
    result = await db.execute(select(MedicineUnit).where(MedicineUnit.name == name, MedicineUnit.is_deleted == False))
    return result.scalars().first()

async def get_medicine_units(
    db: AsyncSession, search: Optional[str] = None, skip: int = 0, limit: int = 100
) -> List[MedicineUnit]:
    query = select(MedicineUnit).where(MedicineUnit.is_deleted == False)
    if search:
        query = query.where(
            (MedicineUnit.name.ilike(f"%{search}%")) | (MedicineUnit.code.ilike(f"%{search}%"))
        )
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())

async def create_medicine_unit(db: AsyncSession, unit: MedicineUnitCreate) -> MedicineUnit:
    db_unit = MedicineUnit(
        name=unit.name,
        code=unit.code,
        is_active=unit.is_active
    )
    db.add(db_unit)
    await db.commit()
    await db.refresh(db_unit)
    return db_unit

async def update_medicine_unit(db: AsyncSession, unit_id: UUID, unit_update: MedicineUnitUpdate) -> Optional[MedicineUnit]:
    db_unit = await get_medicine_unit(db, unit_id)
    if not db_unit:
        return None
    update_data = unit_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_unit, key, value)
    await db.commit()
    await db.refresh(db_unit)
    return db_unit

async def delete_medicine_unit(db: AsyncSession, unit_id: UUID) -> bool:
    db_unit = await get_medicine_unit(db, unit_id)
    if not db_unit:
        return False
    db_unit.is_deleted = True
    await db.commit()
    return True
