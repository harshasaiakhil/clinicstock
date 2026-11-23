from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List, Optional
from app.models.medicine import Potency
from app.schemas.potency import PotencyCreate, PotencyUpdate

async def get_potency(db: AsyncSession, potency_id: UUID) -> Optional[Potency]:
    result = await db.execute(select(Potency).where(Potency.id == potency_id, Potency.is_deleted == False))
    return result.scalars().first()

async def get_potency_by_name(db: AsyncSession, name: str) -> Optional[Potency]:
    result = await db.execute(select(Potency).where(Potency.name == name, Potency.is_deleted == False))
    return result.scalars().first()

async def get_potencies(
    db: AsyncSession, search: Optional[str] = None, skip: int = 0, limit: int = 100
) -> List[Potency]:
    query = select(Potency).where(Potency.is_deleted == False)
    if search:
        query = query.where(Potency.name.ilike(f"%{search}%"))
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())

async def create_potency(db: AsyncSession, potency: PotencyCreate) -> Potency:
    db_potency = Potency(
        name=potency.name,
        is_active=potency.is_active
    )
    db.add(db_potency)
    await db.commit()
    await db.refresh(db_potency)
    return db_potency

async def update_potency(db: AsyncSession, potency_id: UUID, potency_update: PotencyUpdate) -> Optional[Potency]:
    db_potency = await get_potency(db, potency_id)
    if not db_potency:
        return None
    update_data = potency_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_potency, key, value)
    await db.commit()
    await db.refresh(db_potency)
    return db_potency

async def delete_potency(db: AsyncSession, potency_id: UUID) -> bool:
    db_potency = await get_potency(db, potency_id)
    if not db_potency:
        return False
    db_potency.is_deleted = True
    await db.commit()
    return True
