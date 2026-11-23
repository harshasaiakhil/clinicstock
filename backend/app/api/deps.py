from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.core.config import settings
from app.core.database import get_db
from app.crud.user import get_user
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/oauth2",
    auto_error=False
)

async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Extract token from OAuth2 scheme or Authorization header
    auth_token = token
    if not auth_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header.split(" ")[1]

    if not auth_token:
        raise credentials_exception

    try:
        payload = jwt.decode(
            auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user

def get_current_doctor(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges",
        )
    return current_user

from app.core.permissions import Permission, has_permission, get_user_permissions

def require_permission(permission: Permission):
    """
    Dependency factory that verifies if the current active user holds the required permission.
    """
    def _permission_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: Missing required privilege '{permission.value}'"
            )
        return current_user
    return _permission_dependency

def require_role(role: str):
    """
    Dependency factory to enforce role-based access.
    """
    def _role_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if (current_user.role or "").lower() != role.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires '{role}' role"
            )
        return current_user
    return _role_dependency

def enforce_branch_access(
    current_user: User,
    requested_branch_id: Optional[UUID]
) -> Optional[UUID]:
    """
    Enforces branch boundaries on the server side:
    - Assistant users are strictly confined to their assigned default_branch_id.
      Attempting to pass a different branch_id raises HTTP 403 Forbidden.
    - Doctors are permitted to view/manage all branches or filter by a specific branch.
    """
    if current_user.role == "assistant":
        if not current_user.default_branch_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has no assigned branch."
            )
        if requested_branch_id is not None and str(requested_branch_id) != str(current_user.default_branch_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to access another branch."
            )
        return current_user.default_branch_id

    return requested_branch_id
