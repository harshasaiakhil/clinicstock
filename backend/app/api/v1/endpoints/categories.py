from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional

from app.api import deps
from app.crud import category as crud_category
from app.schemas.category import CategoryResponse, CategoryCreate, CategoryUpdate

router = APIRouter()

@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[CategoryResponse]:
    """
    Retrieve categories (accessible by Doctors and Assistants).
    """
    categories = await crud_category.get_categories(db, search=search, skip=skip, limit=limit)
    return categories

@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_active_user),
) -> CategoryResponse:
    """
    Get a category by ID (accessible by Doctors and Assistants).
    """
    category = await crud_category.get_category(db, category_id=category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category

@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_in: CategoryCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
) -> CategoryResponse:
    """
    Create a new category (Doctors only).
    """
    existing = await crud_category.get_category_by_name(db, name=category_in.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists",
        )
    return await crud_category.create_category(db, category=category_in)

@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    category_in: CategoryUpdate,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
) -> CategoryResponse:
    """
    Update a category (Doctors only).
    """
    category = await crud_category.update_category(db, category_id=category_id, category_update=category_in)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(deps.get_db),
    current_user = Depends(deps.get_current_doctor),
):
    """
    Soft delete a category (Doctors only).
    """
    success = await crud_category.delete_category(db, category_id=category_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
