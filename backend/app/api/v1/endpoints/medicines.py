from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional
import io

from app.api import deps
from app.crud import medicine as crud_medicine
from app.schemas.medicine import (
    MedicineResponse,
    MedicineListItemResponse,
    MedicinePaginatedResponse,
    MedicineCreate,
    MedicineUpdate,
    MedicineImportSummary,
)
from app.models.user import User
from app.services.medicine_import import (
    parse_csv_import,
    parse_excel_import,
    generate_csv_export,
    generate_excel_export,
)

router = APIRouter()

def add_price_warning(med) -> Optional[str]:
    return None

@router.get("/", response_model=MedicinePaginatedResponse)
async def list_medicines(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    search: Optional[str] = None,
    category_id: Optional[UUID] = None,
    manufacturer_id: Optional[UUID] = None,
    potency_id: Optional[UUID] = None,
    unit_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 25,
    skip: Optional[int] = None,
    limit: Optional[int] = None,
) -> MedicinePaginatedResponse:
    """
    Retrieve medicines catalog with PostgreSQL-driven search, filtering, and server-side pagination.
    Default page_size: 25, Maximum: 100.
    """
    # Support backward-compatibility if skip/limit passed
    if limit is not None and page_size == 25:
        page_size = min(100, max(1, limit))
    if skip is not None and page == 1 and page_size > 0:
        page = (skip // page_size) + 1

    page = max(1, page)
    page_size = min(100, max(1, page_size))

    medicines, total, pages = await crud_medicine.get_medicines_paginated(
        db,
        search=search,
        category_id=category_id,
        manufacturer_id=manufacturer_id,
        potency_id=potency_id,
        unit_id=unit_id,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    items = []
    for med in medicines:
        res = MedicineListItemResponse.model_validate(med)
        res.warning = add_price_warning(med)
        items.append(res)

    return MedicinePaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        pages=pages,
    )

@router.get("/{medicine_id}", response_model=MedicineResponse)
async def get_medicine(
    medicine_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> MedicineResponse:
    """
    Get medicine details by ID (accessible by Doctors and Assistants).
    """
    med = await crud_medicine.get_medicine(db, medicine_id=medicine_id)
    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine not found")
    
    res = MedicineResponse.model_validate(med)
    res.warning = add_price_warning(med)
    return res

@router.post("/", response_model=MedicineResponse, status_code=status.HTTP_201_CREATED)
async def create_medicine(
    med_in: MedicineCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_doctor),
) -> MedicineResponse:
    """
    Create a new medicine in the catalog (Doctors only).
    """
    # 1. Check unique constraint (Name + Manufacturer + Potency)
    existing = await crud_medicine.get_medicine_by_unique_key(
        db, name=med_in.name, manufacturer_id=med_in.manufacturer_id, potency_id=med_in.potency_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A medicine with this name, manufacturer, and potency already exists.",
        )
        
    created = await crud_medicine.create_medicine(db, medicine=med_in, user_id=current_user.id)
    res = MedicineResponse.model_validate(created)
    res.warning = add_price_warning(created)
    return res

@router.put("/{medicine_id}", response_model=MedicineResponse)
async def update_medicine(
    medicine_id: UUID,
    med_in: MedicineUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_doctor),
) -> MedicineResponse:
    """
    Update medicine details (Doctors only).
    """
    updated = await crud_medicine.update_medicine(
        db, medicine_id=medicine_id, medicine_update=med_in, user_id=current_user.id
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine not found")
        
    res = MedicineResponse.model_validate(updated)
    res.warning = add_price_warning(updated)
    return res

@router.post("/{medicine_id}/activate", response_model=MedicineResponse)
async def activate_medicine(
    medicine_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_doctor),
) -> MedicineResponse:
    """
    Activate a medicine (Doctors only).
    """
    med = await crud_medicine.set_medicine_active_status(
        db, medicine_id=medicine_id, is_active=True, user_id=current_user.id
    )
    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine not found")
        
    res = MedicineResponse.model_validate(med)
    res.warning = add_price_warning(med)
    return res

@router.post("/{medicine_id}/deactivate", response_model=MedicineResponse)
async def deactivate_medicine(
    medicine_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_doctor),
) -> MedicineResponse:
    """
    Deactivate a medicine (Doctors only).
    """
    med = await crud_medicine.set_medicine_active_status(
        db, medicine_id=medicine_id, is_active=False, user_id=current_user.id
    )
    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine not found")
        
    res = MedicineResponse.model_validate(med)
    res.warning = add_price_warning(med)
    return res

@router.post("/import", response_model=MedicineImportSummary)
async def import_medicines(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_doctor),
) -> MedicineImportSummary:
    """
    Bulk import medicines from CSV or Excel file (Doctors only).
    """
    contents = await file.read()
    if file.filename.endswith(".csv"):
        return await parse_csv_import(db, contents, current_user.id)
    elif file.filename.endswith((".xlsx", ".xls")):
        return await parse_excel_import(db, contents, current_user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only CSV and Excel (.xlsx) are supported.",
        )

@router.get("/export/csv")
async def export_csv(
    branch_id: Optional[UUID] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Export medicines to CSV format (accessible by Doctors and Assistants).
    """
    csv_bytes = await generate_csv_export(db, branch_id=branch_id)
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=medicines_export.csv"},
    )

@router.get("/export/excel")
async def export_excel(
    branch_id: Optional[UUID] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Export medicines to Excel format (accessible by Doctors and Assistants).
    """
    excel_bytes = await generate_excel_export(db, branch_id=branch_id)
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=medicines_export.xlsx"},
    )
