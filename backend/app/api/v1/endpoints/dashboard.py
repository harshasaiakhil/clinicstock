from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.api import deps
from app.core.permissions import Permission
from app.crud import dashboard as crud_dashboard
from app.schemas.dashboard import DashboardStatsResponse
from app.models.user import User

router = APIRouter()

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    branch_id: Optional[UUID] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.require_permission(Permission.DASHBOARD_VIEW)),
) -> DashboardStatsResponse:
    """
    Get dashboard analytics statistics.
    Doctors can view system-wide stats or filter by any branch.
    Assistants are strictly confined to their assigned branch stats.
    """
    effective_branch_id = deps.enforce_branch_access(current_user, branch_id)
    return await crud_dashboard.get_dashboard_analytics(db, branch_id=effective_branch_id)
