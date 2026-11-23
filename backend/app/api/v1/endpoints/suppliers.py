from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional

from app.api import deps
from app.crud import supplier as crud_supplier
from app.schemas.supplier import SupplierResponse, SupplierCreate, SupplierUpdate

router = APIRouter()

@router.get("/", response_model=List[SupplierResponse])
async def list_suppliers(
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[SupplierResponse]:
    """
    Retrieve suppliers (accessible by Doctors and Assistants).
    """
    suppliers = await crud_supplier.get_suppliers(db, search=search, skip=skip, limit=limit)
    return suppliers

@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
) -> SupplierResponse:
    """
    Get a supplier by ID (accessible by Doctors and Assistants).
    """
    supplier = await crud_supplier.get_supplier(db, supplier_id=supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return supplier

@router.post("/", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    supplier_in: SupplierCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
) -> SupplierResponse:
    """
    Create a new supplier (Doctors only).
    """
    existing = await crud_supplier.get_supplier_by_name(db, name=supplier_in.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supplier with this name already exists",
        )
    return await crud_supplier.create_supplier(db, supplier=supplier_in)

@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: UUID,
    supplier_in: SupplierUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
) -> SupplierResponse:
    """
    Update a supplier (Doctors only).
    """
    supplier = await crud_supplier.update_supplier(db, supplier_id=supplier_id, supplier_update=supplier_in)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return supplier

@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
):
    """
    Soft delete a supplier (Doctors only).
    """
    success = await crud_supplier.delete_supplier(db, supplier_id=supplier_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
