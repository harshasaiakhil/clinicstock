from pydantic import BaseModel, EmailStr, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Literal
from app.schemas.branch import BranchResponse

class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Literal["doctor", "assistant"] = "assistant"
    default_branch_id: Optional[UUID] = None
    is_active: bool = True
    force_password_change: bool = False

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Minimum 8 characters")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[Literal["doctor", "assistant"]] = None
    default_branch_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    force_password_change: Optional[bool] = None

class UserSummaryResponse(BaseModel):
    id: UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    is_active: bool
    force_password_change: bool = False

    model_config = ConfigDict(from_attributes=True)

class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    default_branch: Optional[BranchResponse] = None

    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PasswordResetRequest(BaseModel):
    new_password: str = Field(..., min_length=8, description="New temporary password (minimum 8 characters)")
    force_password_change: bool = Field(True, description="Require user to change password on next sign in")

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")
    confirm_new_password: str = Field(..., min_length=8, description="Must match new password")
