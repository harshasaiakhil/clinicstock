from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional

from app.api import deps
from app.crud import potency as crud_potency
from app.schemas.potency import PotencyResponse, PotencyCreate, PotencyUpdate

router = APIRouter()

@router.get("/", response_model=List[PotencyResponse])
async def list_potencies(
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[PotencyResponse]:
    """
    Retrieve potencies (accessible by Doctors and Assistants).
    """
    potencies = await crud_potency.get_potencies(db, search=search, skip=skip, limit=limit)
    return potencies

@router.get("/{potency_id}", response_model=PotencyResponse)
async def get_potency(
    potency_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
) -> PotencyResponse:
    """
    Get a potency by ID (accessible by Doctors and Assistants).
    """
    potency = await crud_potency.get_potency(db, potency_id=potency_id)
    if not potency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Potency not found")
    return potency

@router.post("/", response_model=PotencyResponse, status_code=status.HTTP_201_CREATED)
async def create_potency(
    potency_in: PotencyCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
) -> PotencyResponse:
    """
    Create a new potency (Doctors only).
    """
    existing = await crud_potency.get_potency_by_name(db, name=potency_in.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Potency with this name already exists",
        )
    return await crud_potency.create_potency(db, potency=potency_in)

@router.put("/{potency_id}", response_model=PotencyResponse)
async def update_potency(
    potency_id: UUID,
    potency_in: PotencyUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
) -> PotencyResponse:
    """
    Update a potency (Doctors only).
    """
    potency = await crud_potency.update_potency(db, potency_id=potency_id, potency_update=potency_in)
    if not potency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Potency not found")
    return potency

@router.delete("/{potency_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_potency(
    potency_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
):
    """
    Soft delete a potency (Doctors only).
    """
    success = await crud_potency.delete_potency(db, potency_id=potency_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Potency not found")
