from enum import Enum
from typing import Set, Dict, List
from fastapi import HTTPException, status, Depends

from app.models.user import User

class Permission(str, Enum):
    # Dashboard
    DASHBOARD_VIEW = "dashboard.view"

    # Medicines
    MEDICINE_VIEW = "medicine.view"
    MEDICINE_CREATE = "medicine.create"
    MEDICINE_UPDATE = "medicine.update"
    MEDICINE_DELETE = "medicine.delete"

    # Inventory & Stock Operations
    INVENTORY_VIEW = "inventory.view"
    INVENTORY_RECEIVE = "inventory.receive"
    INVENTORY_DISPENSE = "inventory.dispense"
    INVENTORY_ADJUST = "inventory.adjust"
    INVENTORY_TRANSFER = "inventory.transfer"

    # Transactions & Audits
    TRANSACTION_VIEW = "transaction.view"

    # Reports
    REPORT_VIEW = "report.view"
    REPORT_EXPORT = "report.export"

    # Master Data Management
    MASTER_DATA_VIEW = "master_data.view"
    MASTER_DATA_MANAGE = "master_data.manage"

    # User Management & Administration
    USER_VIEW = "user.view"
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_ACTIVATE = "user.activate"
    USER_RESET_PASSWORD = "user.reset_password"

    # Branch Management
    BRANCH_VIEW = "branch.view"
    BRANCH_MANAGE = "branch.manage"

    # System Settings
    SETTINGS_VIEW = "settings.view"
    SETTINGS_MANAGE = "settings.manage"

    # Role Management
    ROLE_VIEW = "role.view"
    ROLE_MANAGE = "role.manage"

ROLE_PERMISSIONS: Dict[str, Set[Permission]] = {
    "doctor": {
        # Full administrative & clinical access
        Permission.DASHBOARD_VIEW,
        Permission.MEDICINE_VIEW,
        Permission.MEDICINE_CREATE,
        Permission.MEDICINE_UPDATE,
        Permission.MEDICINE_DELETE,
        Permission.INVENTORY_VIEW,
        Permission.INVENTORY_RECEIVE,
        Permission.INVENTORY_DISPENSE,
        Permission.INVENTORY_ADJUST,
        Permission.INVENTORY_TRANSFER,
        Permission.TRANSACTION_VIEW,
        Permission.REPORT_VIEW,
        Permission.REPORT_EXPORT,
        Permission.MASTER_DATA_VIEW,
        Permission.MASTER_DATA_MANAGE,
        Permission.USER_VIEW,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.USER_ACTIVATE,
        Permission.USER_RESET_PASSWORD,
        Permission.BRANCH_VIEW,
        Permission.BRANCH_MANAGE,
        Permission.SETTINGS_VIEW,
        Permission.SETTINGS_MANAGE,
        Permission.ROLE_VIEW,
        Permission.ROLE_MANAGE,
    },
    "assistant": {
        # Operational clinic access strictly scoped to assigned branch
        Permission.DASHBOARD_VIEW,
        Permission.MEDICINE_VIEW,
        Permission.INVENTORY_VIEW,
        Permission.INVENTORY_DISPENSE,
        Permission.TRANSACTION_VIEW,
        Permission.REPORT_VIEW,
        Permission.REPORT_EXPORT,
        Permission.BRANCH_VIEW,
    },
}

def has_permission(user: User, permission: Permission) -> bool:
    """Check whether a user has a specific logical permission based on role."""
    if not user or not user.is_active:
        return False
    user_role = (user.role or "").lower()
    allowed_permissions = ROLE_PERMISSIONS.get(user_role, set())
    return permission in allowed_permissions

def get_user_permissions(user: User) -> List[str]:
    """Retrieve all permission string keys granted to the user."""
    if not user or not user.is_active:
        return []
    user_role = (user.role or "").lower()
    return sorted([p.value for p in ROLE_PERMISSIONS.get(user_role, set())])
