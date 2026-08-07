from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.api import deps
from app.crud import dashboard as crud_dashboard
from app.schemas.dashboard import DashboardStatsResponse
from app.models.user import User

router = APIRouter()

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    branch_id: Optional[UUID] = None,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> DashboardStatsResponse:
    """
    Get dashboard analytics statistics.
    Doctors can see system-wide stats or filter by branch.
    Assistants are restricted to their default branch stats.
    """
    # Restrict Assistant to their default branch stats
    if current_user.role == "assistant":
        branch_id = current_user.default_branch_id

    stats = await crud_dashboard.get_dashboard_analytics(db, branch_id=branch_id)
    return stats
