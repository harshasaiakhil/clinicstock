from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List, Optional
from app.models.medicine import Category
from app.schemas.category import CategoryCreate, CategoryUpdate

async def get_category(db: AsyncSession, category_id: UUID) -> Optional[Category]:
    result = await db.execute(select(Category).where(Category.id == category_id, Category.is_deleted == False))
    return result.scalars().first()

async def get_category_by_name(db: AsyncSession, name: str) -> Optional[Category]:
    result = await db.execute(select(Category).where(Category.name == name, Category.is_deleted == False))
    return result.scalars().first()

async def get_categories(
    db: AsyncSession, search: Optional[str] = None, skip: int = 0, limit: int = 100
) -> List[Category]:
    query = select(Category).where(Category.is_deleted == False)
    if search:
        query = query.where(Category.name.ilike(f"%{search}%"))
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())

async def create_category(db: AsyncSession, category: CategoryCreate) -> Category:
    db_category = Category(
        name=category.name,
        description=category.description
    )
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category

async def update_category(db: AsyncSession, category_id: UUID, category_update: CategoryUpdate) -> Optional[Category]:
    db_category = await get_category(db, category_id)
    if not db_category:
        return None
    update_data = category_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_category, key, value)
    await db.commit()
    await db.refresh(db_category)
    return db_category

async def delete_category(db: AsyncSession, category_id: UUID) -> bool:
    db_category = await get_category(db, category_id)
    if not db_category:
        return False
    db_category.is_deleted = True
    await db.commit()
    return True
