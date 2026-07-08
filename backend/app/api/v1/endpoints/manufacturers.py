from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional

from app.api import deps
from app.crud import manufacturer as crud_manufacturer
from app.schemas.manufacturer import ManufacturerResponse, ManufacturerCreate, ManufacturerUpdate

router = APIRouter()

@router.get("/", response_model=List[ManufacturerResponse])
async def list_manufacturers(
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[ManufacturerResponse]:
    """
    Retrieve manufacturers (accessible by Doctors and Assistants).
    """
    manufacturers = await crud_manufacturer.get_manufacturers(db, search=search, skip=skip, limit=limit)
    return manufacturers

@router.get("/{manufacturer_id}", response_model=ManufacturerResponse)
async def get_manufacturer(
    manufacturer_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
) -> ManufacturerResponse:
    """
    Get a manufacturer by ID (accessible by Doctors and Assistants).
    """
    manufacturer = await crud_manufacturer.get_manufacturer(db, manufacturer_id=manufacturer_id)
    if not manufacturer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manufacturer not found")
    return manufacturer

@router.post("/", response_model=ManufacturerResponse, status_code=status.HTTP_201_CREATED)
async def create_manufacturer(
    manufacturer_in: ManufacturerCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
) -> ManufacturerResponse:
    """
    Create a new manufacturer (Doctors only).
    """
    existing = await crud_manufacturer.get_manufacturer_by_name(db, name=manufacturer_in.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manufacturer with this name already exists",
        )
    return await crud_manufacturer.create_manufacturer(db, manufacturer=manufacturer_in)

@router.put("/{manufacturer_id}", response_model=ManufacturerResponse)
async def update_manufacturer(
    manufacturer_id: UUID,
    manufacturer_in: ManufacturerUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
) -> ManufacturerResponse:
    """
    Update a manufacturer (Doctors only).
    """
    manufacturer = await crud_manufacturer.update_manufacturer(db, manufacturer_id=manufacturer_id, manufacturer_update=manufacturer_in)
    if not manufacturer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manufacturer not found")
    return manufacturer

@router.delete("/{manufacturer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_manufacturer(
    manufacturer_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
):
    """
    Soft delete a manufacturer (Doctors only).
    """
    success = await crud_manufacturer.delete_manufacturer(db, manufacturer_id=manufacturer_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manufacturer not found")
