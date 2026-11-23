import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import branch as crud_branch
from app.crud import user as crud_user
from app.schemas.branch import BranchCreate
from app.schemas.user import UserCreate

pytestmark = pytest.mark.asyncio

async def test_master_data_crud_and_permissions(client: AsyncClient, db: AsyncSession):
    # 1. Setup Branch
    branch = await crud_branch.create_branch(
        db, BranchCreate(name="Gudivada Branch", code="GDV_TEST")
    )

    # 2. Setup Doctor
    doctor_in = UserCreate(
        email="doctor@test.com",
        password="Password123",
        first_name="Doctor",
        last_name="Test",
        role="doctor",
        default_branch_id=branch.id
    )
    await crud_user.create_user(db, doctor_in)

    # 3. Setup Assistant
    assistant_in = UserCreate(
        email="assistant@test.com",
        password="Password123",
        first_name="Assistant",
        last_name="Test",
        role="assistant",
        default_branch_id=branch.id
    )
    await crud_user.create_user(db, assistant_in)

    # 4. Get Tokens
    # Doctor Token
    doctor_login = await client.post("/api/v1/auth/login", json={"email": "doctor@test.com", "password": "Password123"})
    doctor_token = doctor_login.json()["access_token"]
    doctor_headers = {"Authorization": f"Bearer {doctor_token}"}

    # Assistant Token
    assistant_login = await client.post("/api/v1/auth/login", json={"email": "assistant@test.com", "password": "Password123"})
    assistant_token = assistant_login.json()["access_token"]
    assistant_headers = {"Authorization": f"Bearer {assistant_token}"}

    # --- Category CRUD ---
    # Create category as Doctor (Success)
    cat_res = await client.post("/api/v1/categories/", json={"name": "Dilutions", "description": "Liquid dilutions"}, headers=doctor_headers)
    assert cat_res.status_code == 201
    cat_data = cat_res.json()
    assert cat_data["name"] == "Dilutions"
    cat_id = cat_data["id"]

    # Create category as Assistant (Forbidden)
    cat_res_fail = await client.post("/api/v1/categories/", json={"name": "Triturations"}, headers=assistant_headers)
    assert cat_res_fail.status_code == 403

    # Read category list as Assistant (Success)
    cat_list = await client.get("/api/v1/categories/", headers=assistant_headers)
    assert cat_list.status_code == 200
    assert len(cat_list.json()) >= 1

    # Update category as Doctor (Success)
    cat_update = await client.put(f"/api/v1/categories/{cat_id}", json={"description": "Liquid dilutions updated"}, headers=doctor_headers)
    assert cat_update.status_code == 200
    assert cat_update.json()["description"] == "Liquid dilutions updated"

    # Delete category as Doctor (Success, soft delete)
    cat_del = await client.delete(f"/api/v1/categories/{cat_id}", headers=doctor_headers)
    assert cat_del.status_code == 204

    # Verify soft deleted category is not in list
    cat_list_after = await client.get("/api/v1/categories/", headers=assistant_headers)
    assert not any(c["id"] == cat_id for c in cat_list_after.json())

    # --- Manufacturer CRUD ---
    # Create manufacturer as Doctor
    man_res = await client.post("/api/v1/manufacturers/", json={"name": "SBL", "description": "SBL India Ltd"}, headers=doctor_headers)
    assert man_res.status_code == 201
    man_id = man_res.json()["id"]

    # Create manufacturer as Assistant (Forbidden)
    man_fail = await client.post("/api/v1/manufacturers/", json={"name": "Schwabe"}, headers=assistant_headers)
    assert man_fail.status_code == 403

    # Read manufacturer list as Assistant (Success)
    man_list = await client.get("/api/v1/manufacturers/", headers=assistant_headers)
    assert man_list.status_code == 200
    assert len(man_list.json()) >= 1

    # Update manufacturer as Doctor
    man_upd = await client.put(f"/api/v1/manufacturers/{man_id}", json={"description": "SBL India updated"}, headers=doctor_headers)
    assert man_upd.status_code == 200
    assert man_upd.json()["description"] == "SBL India updated"

    # Delete manufacturer
    man_del = await client.delete(f"/api/v1/manufacturers/{man_id}", headers=doctor_headers)
    assert man_del.status_code == 204

    # --- Supplier CRUD ---
    # Create supplier as Doctor
    sup_res = await client.post("/api/v1/suppliers/", json={"name": "AP Pharmacy", "email": "ap@pharmacy.com", "phone": "1234567890"}, headers=doctor_headers)
    assert sup_res.status_code == 201
    sup_id = sup_res.json()["id"]

    # Create supplier as Assistant (Forbidden)
    sup_fail = await client.post("/api/v1/suppliers/", json={"name": "State Pharmacy"}, headers=assistant_headers)
    assert sup_fail.status_code == 403

    # Read supplier as Assistant (Success)
    sup_list = await client.get("/api/v1/suppliers/", headers=assistant_headers)
    assert sup_list.status_code == 200
    assert len(sup_list.json()) >= 1

    # Update supplier
    sup_upd = await client.put(f"/api/v1/suppliers/{sup_id}", json={"contact_name": "Akhil"}, headers=doctor_headers)
    assert sup_upd.status_code == 200
    assert sup_upd.json()["contact_name"] == "Akhil"

    # Delete supplier
    sup_del = await client.delete(f"/api/v1/suppliers/{sup_id}", headers=doctor_headers)
    assert sup_del.status_code == 204

    # --- Medicine Unit CRUD ---
    # Create unit as Doctor
    unit_res = await client.post("/api/v1/medicine-units/", json={"name": "TestUnit", "code": "TST"}, headers=doctor_headers)
    assert unit_res.status_code == 201
    unit_id = unit_res.json()["id"]

    # Read list
    unit_list = await client.get("/api/v1/medicine-units/", headers=assistant_headers)
    assert unit_list.status_code == 200

    # Update unit
    unit_upd = await client.put(f"/api/v1/medicine-units/{unit_id}", json={"name": "TestUnitUpdated"}, headers=doctor_headers)
    assert unit_upd.status_code == 200

    # Delete unit
    unit_del = await client.delete(f"/api/v1/medicine-units/{unit_id}", headers=doctor_headers)
    assert unit_del.status_code == 204

    # --- Potency CRUD ---
    # Create potency as Doctor
    pot_res = await client.post("/api/v1/potencies/", json={"name": "30C_TEST"}, headers=doctor_headers)
    assert pot_res.status_code == 201
    pot_id = pot_res.json()["id"]

    # Read list
    pot_list = await client.get("/api/v1/potencies/", headers=assistant_headers)
    assert pot_list.status_code == 200

    # Update potency
    pot_upd = await client.put(f"/api/v1/potencies/{pot_id}", json={"name": "30C_TEST_UPD"}, headers=doctor_headers)
    assert pot_upd.status_code == 200

    # Delete potency
    pot_del = await client.delete(f"/api/v1/potencies/{pot_id}", headers=doctor_headers)
    assert pot_del.status_code == 204
