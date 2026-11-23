from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List, Optional
from app.models.medicine import Manufacturer
from app.schemas.manufacturer import ManufacturerCreate, ManufacturerUpdate

async def get_manufacturer(db: AsyncSession, manufacturer_id: UUID) -> Optional[Manufacturer]:
    result = await db.execute(select(Manufacturer).where(Manufacturer.id == manufacturer_id, Manufacturer.is_deleted == False))
    return result.scalars().first()

async def get_manufacturer_by_name(db: AsyncSession, name: str) -> Optional[Manufacturer]:
    result = await db.execute(select(Manufacturer).where(Manufacturer.name == name, Manufacturer.is_deleted == False))
    return result.scalars().first()

async def get_manufacturers(
    db: AsyncSession, search: Optional[str] = None, skip: int = 0, limit: int = 100
) -> List[Manufacturer]:
    query = select(Manufacturer).where(Manufacturer.is_deleted == False)
    if search:
        query = query.where(Manufacturer.name.ilike(f"%{search}%"))
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())

async def create_manufacturer(db: AsyncSession, manufacturer: ManufacturerCreate) -> Manufacturer:
    db_manufacturer = Manufacturer(
        name=manufacturer.name,
        description=manufacturer.description
    )
    db.add(db_manufacturer)
    await db.commit()
    await db.refresh(db_manufacturer)
    return db_manufacturer

async def update_manufacturer(db: AsyncSession, manufacturer_id: UUID, manufacturer_update: ManufacturerUpdate) -> Optional[Manufacturer]:
    db_manufacturer = await get_manufacturer(db, manufacturer_id)
    if not db_manufacturer:
        return None
    update_data = manufacturer_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_manufacturer, key, value)
    await db.commit()
    await db.refresh(db_manufacturer)
    return db_manufacturer

async def delete_manufacturer(db: AsyncSession, manufacturer_id: UUID) -> bool:
    db_manufacturer = await get_manufacturer(db, manufacturer_id)
    if not db_manufacturer:
        return False
    db_manufacturer.is_deleted = True
    await db.commit()
    return True
