from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List, Optional
from app.models.branch import Branch
from app.schemas.branch import BranchCreate, BranchUpdate

async def get_branch(db: AsyncSession, branch_id: UUID) -> Optional[Branch]:
    result = await db.execute(select(Branch).where(Branch.id == branch_id))
    return result.scalars().first()

async def get_branch_by_code(db: AsyncSession, code: str) -> Optional[Branch]:
    result = await db.execute(select(Branch).where(Branch.code == code))
    return result.scalars().first()

async def get_branches(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Branch]:
    result = await db.execute(select(Branch).offset(skip).limit(limit))
    return list(result.scalars().all())

async def create_branch(db: AsyncSession, branch: BranchCreate) -> Branch:
    db_branch = Branch(
        name=branch.name,
        code=branch.code,
        address=branch.address,
        phone=branch.phone,
        is_active=branch.is_active
    )
    db.add(db_branch)
    await db.commit()
    await db.refresh(db_branch)
    return db_branch

async def update_branch(db: AsyncSession, branch_id: UUID, branch_update: BranchUpdate) -> Optional[Branch]:
    db_branch = await get_branch(db, branch_id)
    if not db_branch:
        return None
    update_data = branch_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_branch, key, value)
    await db.commit()
    await db.refresh(db_branch)
    return db_branch
