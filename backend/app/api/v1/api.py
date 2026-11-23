from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    users,
    branches,
    categories,
    manufacturers,
    suppliers,
    medicine_units,
    potencies,
    medicines,
    inventory,
    dashboard,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(branches.router, prefix="/branches", tags=["branches"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(manufacturers.router, prefix="/manufacturers", tags=["manufacturers"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(medicine_units.router, prefix="/medicine-units", tags=["medicine-units"])
api_router.include_router(potencies.router, prefix="/potencies", tags=["potencies"])
api_router.include_router(medicines.router, prefix="/medicines", tags=["medicines"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
