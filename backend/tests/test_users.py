import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import branch as crud_branch
from app.crud import user as crud_user
from app.schemas.branch import BranchCreate
from app.schemas.user import UserCreate

pytestmark = pytest.mark.asyncio

async def setup_test_users(client: AsyncClient, db: AsyncSession):
    """Helper to create branches, doctor, and assistant with auth tokens."""
    branch = await crud_branch.create_branch(
        db, BranchCreate(name="Vijayawada Branch", code="VJA_SEC")
    )

    doctor = await crud_user.create_user(
        db,
        UserCreate(
            email="dr.sec@clinicstock.com",
            password="DoctorPassword123",
            first_name="Doctor",
            last_name="Primary",
            role="doctor",
            default_branch_id=branch.id,
        ),
    )

    assistant = await crud_user.create_user(
        db,
        UserCreate(
            email="ast.sec@clinicstock.com",
            password="AssistantPassword123",
            first_name="Assistant",
            last_name="Staff",
            role="assistant",
            default_branch_id=branch.id,
        ),
    )

    # Login doctor
    doc_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "dr.sec@clinicstock.com", "password": "DoctorPassword123"},
    )
    doc_token = doc_res.json()["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    # Login assistant
    ast_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "ast.sec@clinicstock.com", "password": "AssistantPassword123"},
    )
    ast_token = ast_res.json()["access_token"]
    ast_headers = {"Authorization": f"Bearer {ast_token}"}

    return branch, doctor, assistant, doc_headers, ast_headers


async def test_doctor_can_list_users(client: AsyncClient, db: AsyncSession):
    _, _, _, doc_headers, _ = await setup_test_users(client, db)
    res = await client.get("/api/v1/users/", headers=doc_headers)
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 2


async def test_assistant_cannot_list_users(client: AsyncClient, db: AsyncSession):
    _, _, _, _, ast_headers = await setup_test_users(client, db)
    res = await client.get("/api/v1/users/", headers=ast_headers)
    assert res.status_code == 403
    assert "Permission denied" in res.json()["detail"]


async def test_assistant_cannot_create_user(client: AsyncClient, db: AsyncSession):
    branch, _, _, _, ast_headers = await setup_test_users(client, db)
    new_user = {
        "email": "hacker@clinicstock.com",
        "password": "Password123",
        "first_name": "Bad",
        "last_name": "Actor",
        "role": "doctor",
        "default_branch_id": str(branch.id),
    }
    res = await client.post("/api/v1/users/", json=new_user, headers=ast_headers)
    assert res.status_code == 403


async def test_doctor_can_reset_assistant_password(client: AsyncClient, db: AsyncSession):
    _, _, assistant, doc_headers, _ = await setup_test_users(client, db)

    # Doctor resets Assistant's password to TempPass@2026
    payload = {
        "new_password": "TempPass@2026",
        "force_password_change": True,
    }
    res = await client.post(
        f"/api/v1/users/{assistant.id}/reset-password",
        json=payload,
        headers=doc_headers,
    )
    assert res.status_code == 200
    updated_user = res.json()
    assert updated_user["force_password_change"] is True

    # Assistant old password should now fail
    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "ast.sec@clinicstock.com", "password": "AssistantPassword123"},
    )
    assert old_login.status_code == 400

    # Assistant can login with new temporary password
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "ast.sec@clinicstock.com", "password": "TempPass@2026"},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()


async def test_assistant_cannot_reset_passwords(client: AsyncClient, db: AsyncSession):
    _, doctor, _, _, ast_headers = await setup_test_users(client, db)
    payload = {
        "new_password": "HackedPassword123",
        "force_password_change": False,
    }
    res = await client.post(
        f"/api/v1/users/{doctor.id}/reset-password",
        json=payload,
        headers=ast_headers,
    )
    assert res.status_code == 403


async def test_user_can_change_own_password(client: AsyncClient, db: AsyncSession):
    _, _, _, _, ast_headers = await setup_test_users(client, db)

    # 1. Wrong current password -> 400
    res_wrong = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "WrongCurrentPassword",
            "new_password": "BrandNewPassword123",
            "confirm_new_password": "BrandNewPassword123",
        },
        headers=ast_headers,
    )
    assert res_wrong.status_code == 400
    assert "Incorrect current password" in res_wrong.json()["detail"]

    # 2. Confirmation mismatch -> 400
    res_mismatch = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "AssistantPassword123",
            "new_password": "BrandNewPassword123",
            "confirm_new_password": "DifferentPassword123",
        },
        headers=ast_headers,
    )
    assert res_mismatch.status_code == 400
    assert "do not match" in res_mismatch.json()["detail"]

    # 3. Same as current password -> 400
    res_same = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "AssistantPassword123",
            "new_password": "AssistantPassword123",
            "confirm_new_password": "AssistantPassword123",
        },
        headers=ast_headers,
    )
    assert res_same.status_code == 400
    assert "must be different" in res_same.json()["detail"]

    # 4. Successful change
    res_ok = await client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "AssistantPassword123",
            "new_password": "BrandNewPassword123",
            "confirm_new_password": "BrandNewPassword123",
        },
        headers=ast_headers,
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "success"

    # 5. Verify can login with new password
    login_ok = await client.post(
        "/api/v1/auth/login",
        json={"email": "ast.sec@clinicstock.com", "password": "BrandNewPassword123"},
    )
    assert login_ok.status_code == 200


async def test_doctor_self_protection_safeguards(client: AsyncClient, db: AsyncSession):
    _, doctor, assistant, doc_headers, _ = await setup_test_users(client, db)

    # 1. Doctor cannot deactivate own account
    deact_self = await client.post(
        f"/api/v1/users/{doctor.id}/deactivate",
        headers=doc_headers,
    )
    assert deact_self.status_code == 400
    assert "cannot deactivate your own account" in deact_self.json()["detail"]

    # 2. Doctor cannot demote own role
    demote_self = await client.put(
        f"/api/v1/users/{doctor.id}",
        json={"role": "assistant"},
        headers=doc_headers,
    )
    assert demote_self.status_code == 400
    assert "cannot remove your own doctor administrative role" in demote_self.json()["detail"]

    # 3. Doctor CAN deactivate assistant
    deact_ast = await client.post(
        f"/api/v1/users/{assistant.id}/deactivate",
        headers=doc_headers,
    )
    assert deact_ast.status_code == 200
    assert deact_ast.json()["is_active"] is False

    # 4. Deactivated assistant cannot log in
    ast_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "ast.sec@clinicstock.com", "password": "AssistantPassword123"},
    )
    assert ast_login.status_code == 400
    assert "Inactive user" in ast_login.json()["detail"]

    # 5. Doctor can reactivate assistant
    react_ast = await client.post(
        f"/api/v1/users/{assistant.id}/activate",
        headers=doc_headers,
    )
    assert react_ast.status_code == 200
    assert react_ast.json()["is_active"] is True
