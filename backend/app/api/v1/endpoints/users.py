from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.api import deps
from app.crud import user as crud_user
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_doctor),
    skip: int = 0,
    limit: int = 100
) -> List[UserResponse]:
    """
    List all users (restricted to Doctors).
    """
    users = await crud_user.get_users(db, skip=skip, limit=limit)
    return users

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_doctor),
) -> UserResponse:
    """
    Create a new user (restricted to Doctors).
    """
    existing_user = await crud_user.get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )
    return await crud_user.create_user(db, user=user_in)

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> UserResponse:
    """
    Update a user. Active users can update themselves; only doctors can update other users or change roles.
    """
    # Permission check
    if current_user.role != "doctor" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this user",
        )

    # Prevent non-doctor from elevating role or branch
    if current_user.role != "doctor":
        user_in.role = None
        user_in.is_active = None

    updated = await crud_user.update_user(db, user_id=user_id, user_update=user_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return updated
