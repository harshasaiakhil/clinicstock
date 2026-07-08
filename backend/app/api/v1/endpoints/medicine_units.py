from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional

from app.api import deps
from app.crud import medicine_unit as crud_unit
from app.schemas.medicine_unit import MedicineUnitResponse, MedicineUnitCreate, MedicineUnitUpdate

router = APIRouter()

@router.get("/", response_model=List[MedicineUnitResponse])
async def list_medicine_units(
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[MedicineUnitResponse]:
    """
    Retrieve medicine units (accessible by Doctors and Assistants).
    """
    units = await crud_unit.get_medicine_units(db, search=search, skip=skip, limit=limit)
    return units

@router.get("/{unit_id}", response_model=MedicineUnitResponse)
async def get_medicine_unit(
    unit_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
) -> MedicineUnitResponse:
    """
    Get a medicine unit by ID (accessible by Doctors and Assistants).
    """
    unit = await crud_unit.get_medicine_unit(db, unit_id=unit_id)
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine unit not found")
    return unit

@router.post("/", response_model=MedicineUnitResponse, status_code=status.HTTP_201_CREATED)
async def create_medicine_unit(
    unit_in: MedicineUnitCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
) -> MedicineUnitResponse:
    """
    Create a new medicine unit (Doctors only).
    """
    existing_name = await crud_unit.get_medicine_unit_by_name(db, name=unit_in.name)
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medicine unit with this name already exists",
        )
    existing_code = await crud_unit.get_medicine_unit_by_code(db, code=unit_in.code)
    if existing_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medicine unit with this code already exists",
        )
    return await crud_unit.create_medicine_unit(db, unit=unit_in)

@router.put("/{unit_id}", response_model=MedicineUnitResponse)
async def update_medicine_unit(
    unit_id: UUID,
    unit_in: MedicineUnitUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
) -> MedicineUnitResponse:
    """
    Update a medicine unit (Doctors only).
    """
    unit = await crud_unit.update_medicine_unit(db, unit_id=unit_id, unit_update=unit_in)
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine unit not found")
    return unit

@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medicine_unit(
    unit_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
):
    """
    Soft delete a medicine unit (Doctors only).
    """
    success = await crud_unit.delete_medicine_unit(db, unit_id=unit_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine unit not found")
