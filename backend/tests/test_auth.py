import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import branch as crud_branch
from app.schemas.branch import BranchCreate

pytestmark = pytest.mark.asyncio

async def test_login_and_auth_flow(client: AsyncClient, db: AsyncSession):
    # 1. Create a branch for default association
    branch = await crud_branch.create_branch(
        db,
        BranchCreate(name="Gudivada Branch", code="GDV_TEST")
    )

    # 2. Register/Create a user directly in database
    from app.crud import user as crud_user
    from app.schemas.user import UserCreate

    doctor_in = UserCreate(
        email="doctor_test@clinicstock.com",
        password="Password123",
        first_name="Test",
        last_name="Doctor",
        role="doctor",
        default_branch_id=branch.id
    )
    user = await crud_user.create_user(db, doctor_in)
    assert user.email == "doctor_test@clinicstock.com"

    # 3. Test failed login
    login_data_fail = {"email": "doctor_test@clinicstock.com", "password": "WrongPassword"}
    response = await client.post("/api/v1/auth/login", json=login_data_fail)
    assert response.status_code == 400

    # 4. Test successful login
    login_data = {"email": "doctor_test@clinicstock.com", "password": "Password123"}
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    token_response = response.json()
    assert "access_token" in token_response
    assert token_response["token_type"] == "bearer"

    # 5. Access /me endpoint with token
    headers = {"Authorization": f"Bearer {token_response['access_token']}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    profile = response.json()
    assert profile["email"] == "doctor_test@clinicstock.com"
    assert profile["role"] == "doctor"

    # 6. Create another user using the Doctor auth token
    new_user_data = {
        "email": "assistant_test@clinicstock.com",
        "password": "Password456",
        "first_name": "Test",
        "last_name": "Assistant",
        "role": "assistant",
        "default_branch_id": str(branch.id)
    }
    response = await client.post("/api/v1/users/", json=new_user_data, headers=headers)
    assert response.status_code == 201
    assistant_profile = response.json()
    assert assistant_profile["email"] == "assistant_test@clinicstock.com"
    assert assistant_profile["role"] == "assistant"
