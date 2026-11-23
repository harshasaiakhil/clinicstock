from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.api import deps
from app.crud import branch as crud_branch
from app.schemas.branch import BranchResponse, BranchCreate, BranchUpdate

router = APIRouter()

@router.get("/", response_model=List[BranchResponse])
async def list_branches(
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 100
) -> List[BranchResponse]:
    """
    Retrieve branches (viewable by all active users).
    """
    branches = await crud_branch.get_branches(db, skip=skip, limit=limit)
    return branches

@router.post("/", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(
    branch_in: BranchCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
) -> BranchResponse:
    """
    Create a new branch (restricted to Doctors).
    """
    existing_branch = await crud_branch.get_branch_by_code(db, code=branch_in.code)
    if existing_branch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Branch with this code already exists",
        )
    return await crud_branch.create_branch(db, branch=branch_in)

@router.put("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: UUID,
    branch_in: BranchUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
) -> BranchResponse:
    """
    Update branch properties (restricted to Doctors).
    """
    branch = await crud_branch.update_branch(db, branch_id=branch_id, branch_update=branch_in)
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )
    return branch
