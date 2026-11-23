from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.api import deps
from app.core.permissions import Permission
from app.crud import user as crud_user
from app.schemas.user import UserResponse, UserCreate, UserUpdate, PasswordResetRequest
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_permission(Permission.USER_VIEW)),
    skip: int = 0,
    limit: int = 100,
) -> List[UserResponse]:
    """
    List all clinic users (restricted to users with user.view permission / Doctors).
    """
    return await crud_user.get_users(db, skip=skip, limit=limit)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> UserResponse:
    """
    Retrieve user details by ID. Users can view themselves; other profiles require user.view.
    """
    if current_user.id != user_id and not deps.has_permission(current_user, Permission.USER_VIEW):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You cannot view other user profiles",
        )

    user = await crud_user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_permission(Permission.USER_CREATE)),
) -> UserResponse:
    """
    Create a new user (restricted to Doctors/Admins).
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
    Update a user profile.
    - Active users can update their own personal details (name).
    - Doctors can update roles, branches, and other users.
    - Safeguard: A Doctor cannot remove their own Doctor role.
    """
    is_doctor = deps.has_permission(current_user, Permission.USER_UPDATE)
    is_self = current_user.id == user_id

    if not is_doctor and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: You are not authorized to update this user",
        )

    # Self-protection safeguard: prevent doctor from removing their own administrative role
    if is_self and user_in.role is not None and user_in.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Safety restriction: You cannot remove your own doctor administrative role",
        )

    # Prevent non-doctor from changing role or active status
    if not is_doctor:
        user_in.role = None
        user_in.is_active = None
        user_in.default_branch_id = None
        user_in.force_password_change = None

    updated = await crud_user.update_user(db, user_id=user_id, user_update=user_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return updated

@router.post("/{user_id}/reset-password", response_model=UserResponse)
async def reset_password_for_user(
    user_id: UUID,
    payload: PasswordResetRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_permission(Permission.USER_RESET_PASSWORD)),
) -> UserResponse:
    """
    Reset another user's password (Doctors/Admins only).
    Sets a new temporary password and optionally requires password change on next login.
    """
    target_user = await crud_user.get_user(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found",
        )

    updated_user = await crud_user.reset_user_password(
        db,
        user_id=user_id,
        new_password=payload.new_password,
        force_password_change=payload.force_password_change,
    )
    return updated_user

@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_permission(Permission.USER_ACTIVATE)),
) -> UserResponse:
    """
    Activate a user account.
    """
    updated = await crud_user.set_user_active_status(db, user_id=user_id, is_active=True)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated

@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_permission(Permission.USER_ACTIVATE)),
) -> UserResponse:
    """
    Deactivate a user account.
    Safeguard: A Doctor cannot deactivate their own account (prevents accidental lockout).
    """
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Safety restriction: You cannot deactivate your own account",
        )

    updated = await crud_user.set_user_active_status(db, user_id=user_id, is_active=False)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated
