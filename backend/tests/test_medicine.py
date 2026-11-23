import pytest
import io
import pandas as pd
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import branch as crud_branch
from app.crud import user as crud_user
from app.crud import category as crud_category
from app.crud import manufacturer as crud_manufacturer
from app.crud import potency as crud_potency
from app.crud import medicine_unit as crud_unit
from app.schemas.branch import BranchCreate
from app.schemas.user import UserCreate
from app.schemas.category import CategoryCreate
from app.schemas.manufacturer import ManufacturerCreate
from app.schemas.potency import PotencyCreate
from app.schemas.medicine_unit import MedicineUnitCreate

pytestmark = pytest.mark.asyncio

async def test_medicine_catalog_flow(client: AsyncClient, db: AsyncSession):
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

    # 4. Get Headers
    doctor_login = await client.post("/api/v1/auth/login", json={"email": "doctor@test.com", "password": "Password123"})
    doctor_headers = {"Authorization": f"Bearer {doctor_login.json()['access_token']}"}

    assistant_login = await client.post("/api/v1/auth/login", json={"email": "assistant@test.com", "password": "Password123"})
    assistant_headers = {"Authorization": f"Bearer {assistant_login.json()['access_token']}"}

    # 5. Seed Master Entities
    cat = await crud_category.create_category(db, CategoryCreate(name="Dilutions", description="Liquid dilutions"))
    man_sbl = await crud_manufacturer.create_manufacturer(db, ManufacturerCreate(name="SBL", description="SBL India"))
    man_schwabe = await crud_manufacturer.create_manufacturer(db, ManufacturerCreate(name="Schwabe", description="Schwabe Germany"))
    pot_30c = await crud_potency.create_potency(db, PotencyCreate(name="30C"))
    pot_200c = await crud_potency.create_potency(db, PotencyCreate(name="200C"))
    unit_btl = await crud_unit.create_medicine_unit(db, MedicineUnitCreate(name="Bottle", code="BTL"))

    # 6. Test Create Medicine as Doctor (Success)
    med_in = {
        "name": "Arnica Montana",
        "generic_name": "Arnica",
        "category_id": str(cat.id),
        "manufacturer_id": str(man_sbl.id),
        "potency_id": str(pot_30c.id),
        "unit_id": str(unit_btl.id),
        "quantity": 10,
        "selling_price": 120.0,
        "gst_percentage": 5.0,
        "hsn_code": "HSN123",
        "description": "Anti-inflammatory homeopathy remedy",
        "is_active": True
    }
    create_res = await client.post("/api/v1/medicines/", json=med_in, headers=doctor_headers)
    assert create_res.status_code == 201
    med_data = create_res.json()
    assert med_data["name"] == "Arnica Montana"
    assert med_data["warning"] is None
    med_id = med_data["id"]

    # 7. Test Create Medicine as Assistant (Forbidden)
    create_res_fail = await client.post("/api/v1/medicines/", json=med_in, headers=assistant_headers)
    assert create_res_fail.status_code == 403

    # 8. Test Negative Quantity Validation Error (FastAPI validation)
    med_neg_q_in = med_in.copy()
    med_neg_q_in["name"] = "Aconitum Napellus"
    med_neg_q_in["quantity"] = -5
    neg_q_res = await client.post("/api/v1/medicines/", json=med_neg_q_in, headers=doctor_headers)
    assert neg_q_res.status_code == 422  # Unprocessable Entity

    # 9. Test Negative Selling Price Validation Error
    med_neg_in = med_in.copy()
    med_neg_in["name"] = "Bryonia"
    med_neg_in["selling_price"] = -5.0
    neg_res = await client.post("/api/v1/medicines/", json=med_neg_in, headers=doctor_headers)
    assert neg_res.status_code == 422  # Unprocessable Entity

    # 9b. Create Aconitum Napellus (Success)
    med_valid_in = med_in.copy()
    med_valid_in["name"] = "Aconitum Napellus"
    med_valid_in["quantity"] = 15
    create_valid_res = await client.post("/api/v1/medicines/", json=med_valid_in, headers=doctor_headers)
    assert create_valid_res.status_code == 201

    # 10. Test Duplicate Validation (Name + Manufacturer + Potency must be unique)
    dup_res = await client.post("/api/v1/medicines/", json=med_in, headers=doctor_headers)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

    # 11. Test Get Medicine by ID
    get_res = await client.get(f"/api/v1/medicines/{med_id}", headers=assistant_headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Arnica Montana"
    assert get_res.json()["category"]["name"] == "Dilutions"

    # 12. Test Update Medicine
    update_res = await client.put(f"/api/v1/medicines/{med_id}", json={"selling_price": 130.0}, headers=doctor_headers)
    assert update_res.status_code == 200
    assert update_res.json()["selling_price"] == 130.0

    # 13. Test Search & Filter
    search_res = await client.get("/api/v1/medicines/?search=arnica", headers=assistant_headers)
    assert search_res.status_code == 200
    search_json = search_res.json()
    search_items = search_json["items"] if isinstance(search_json, dict) and "items" in search_json else search_json
    assert len(search_items) >= 1

    filter_res = await client.get(f"/api/v1/medicines/?category_id={cat.id}&is_active=true", headers=assistant_headers)
    assert filter_res.status_code == 200
    filter_json = filter_res.json()
    filter_items = filter_json["items"] if isinstance(filter_json, dict) and "items" in filter_json else filter_json
    assert len(filter_items) >= 2

    # 14. Test Activate / Deactivate
    deact_res = await client.post(f"/api/v1/medicines/{med_id}/deactivate", headers=doctor_headers)
    assert deact_res.status_code == 200
    assert deact_res.json()["is_active"] is False

    act_res = await client.post(f"/api/v1/medicines/{med_id}/activate", headers=doctor_headers)
    assert act_res.status_code == 200
    assert act_res.json()["is_active"] is True

    # 15. Test Export CSV / Excel
    csv_export = await client.get("/api/v1/medicines/export/csv", headers=assistant_headers)
    assert csv_export.status_code == 200
    assert csv_export.headers["Content-Type"] == "text/csv; charset=utf-8"

    excel_export = await client.get("/api/v1/medicines/export/excel", headers=assistant_headers)
    assert excel_export.status_code == 200
    assert "spreadsheet" in excel_export.headers["Content-Type"]

    # 16. Test CSV Import
    # Format of CSV matching seed master data
    csv_content = """Name,Generic Name,Category,Manufacturer,Potency,Unit,Purchase Price,Selling Price,GST Percentage,HSN Code,Description,Active
Arnica Montana,Arnica,Dilutions,SBL,30C,Bottle,100,120,5,HSN123,Anti-inflammatory,True
Nux Vomica,Nux,Dilutions,Schwabe,30C,Bottle,150,180,5,HSN789,,True
Arnica Montana,Arnica,Dilutions,SBL,30C,Bottle,100,120,5,HSN123,Duplicate row,True
"""
    files = {"file": ("medicines.csv", csv_content, "text/csv")}
    import_res = await client.post("/api/v1/medicines/import", files=files, headers=doctor_headers)
    assert import_res.status_code == 200
    summary = import_res.json()
    
    # Summary assertions:
    # 1. Arnica Montana already exists in database -> it should be updated (updated = 1)
    # 2. Nux Vomica is new -> it should be imported (imported = 1)
    # 3. Arnica Montana row 3 is duplicate in file -> (duplicate_rows = 1)
    assert summary["updated"] == 1
    assert summary["imported"] == 1
    assert summary["duplicate_rows"] == 1
    assert summary["failed"] == 0
