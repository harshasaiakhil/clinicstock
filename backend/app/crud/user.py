from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List, Optional, Tuple
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password

async def get_user(db: AsyncSession, user_id: UUID) -> Optional[User]:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.default_branch))
    )
    return result.scalars().first()

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(
        select(User)
        .where(User.email == email)
        .options(selectinload(User.default_branch))
    )
    return result.scalars().first()

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
        .options(selectinload(User.default_branch))
    )
    return list(result.scalars().all())

async def create_user(db: AsyncSession, user: UserCreate) -> User:
    db_user = User(
        email=user.email,
        password_hash=get_password_hash(user.password),
        first_name=user.first_name,
        last_name=user.last_name,
        role=(user.role or "assistant").lower(),
        default_branch_id=user.default_branch_id,
        is_active=user.is_active,
        force_password_change=user.force_password_change,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return await get_user(db, db_user.id)

async def update_user(db: AsyncSession, user_id: UUID, user_update: UserUpdate) -> Optional[User]:
    db_user = await get_user(db, user_id)
    if not db_user:
        return None

    update_data = user_update.model_dump(exclude_unset=True)
    if "password" in update_data:
        password = update_data.pop("password")
        if password:
            db_user.password_hash = get_password_hash(password)

    if "role" in update_data and update_data["role"]:
        update_data["role"] = update_data["role"].lower()

    for key, value in update_data.items():
        setattr(db_user, key, value)

    await db.commit()
    await db.refresh(db_user)
    return await get_user(db, db_user.id)

async def reset_user_password(
    db: AsyncSession, user_id: UUID, new_password: str, force_password_change: bool = True
) -> Optional[User]:
    db_user = await get_user(db, user_id)
    if not db_user:
        return None

    db_user.password_hash = get_password_hash(new_password)
    db_user.force_password_change = force_password_change
    await db.commit()
    await db.refresh(db_user)
    return await get_user(db, db_user.id)

async def change_user_password(
    db: AsyncSession, user_id: UUID, current_password: str, new_password: str
) -> Tuple[bool, str]:
    db_user = await get_user(db, user_id)
    if not db_user:
        return False, "User not found"

    if not verify_password(current_password, db_user.password_hash):
        return False, "Incorrect current password"

    db_user.password_hash = get_password_hash(new_password)
    db_user.force_password_change = False
    await db.commit()
    await db.refresh(db_user)
    return True, "Password changed successfully"

async def set_user_active_status(
    db: AsyncSession, user_id: UUID, is_active: bool
) -> Optional[User]:
    db_user = await get_user(db, user_id)
    if not db_user:
        return None

    db_user.is_active = is_active
    await db.commit()
    await db.refresh(db_user)
    return await get_user(db, db_user.id)

async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
