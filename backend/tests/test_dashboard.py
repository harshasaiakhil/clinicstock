import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta
from uuid import UUID

from app.crud import branch as crud_branch
from app.crud import user as crud_user
from app.crud import category as crud_category
from app.crud import manufacturer as crud_manufacturer
from app.crud import potency as crud_potency
from app.crud import medicine_unit as crud_unit
from app.crud import medicine as crud_medicine
from app.schemas.branch import BranchCreate
from app.schemas.user import UserCreate
from app.schemas.category import CategoryCreate
from app.schemas.manufacturer import ManufacturerCreate
from app.schemas.potency import PotencyCreate
from app.schemas.medicine_unit import MedicineUnitCreate
from app.schemas.medicine import MedicineCreate

pytestmark = pytest.mark.asyncio

async def test_dashboard_analytics_flow(client: AsyncClient, db: AsyncSession):
    # 1. Setup Branches
    gdv_branch = await crud_branch.create_branch(db, BranchCreate(name="Gudivada", code="GDV"))
    kkl_branch = await crud_branch.create_branch(db, BranchCreate(name="Kaikaluru", code="KKL"))

    # 2. Setup Users
    doc_in = UserCreate(
        email="doc@test.com", password="Password123", first_name="Doc", last_name="Test", role="doctor", default_branch_id=gdv_branch.id
    )
    await crud_user.create_user(db, doc_in)

    asst_in = UserCreate(
        email="asst@test.com", password="Password123", first_name="Asst", last_name="Test", role="assistant", default_branch_id=kkl_branch.id
    )
    await crud_user.create_user(db, asst_in)

    # 3. Headers
    doc_login = await client.post("/api/v1/auth/login", json={"email": "doc@test.com", "password": "Password123"})
    doc_headers = {"Authorization": f"Bearer {doc_login.json()['access_token']}"}

    asst_login = await client.post("/api/v1/auth/login", json={"email": "asst@test.com", "password": "Password123"})
    asst_headers = {"Authorization": f"Bearer {asst_login.json()['access_token']}"}

    # 4. Seed Masters & Medicine
    cat = await crud_category.create_category(db, CategoryCreate(name="Dilutions"))
    man = await crud_manufacturer.create_manufacturer(db, ManufacturerCreate(name="SBL"))
    pot = await crud_potency.create_potency(db, PotencyCreate(name="30C"))
    unit = await crud_unit.create_medicine_unit(db, MedicineUnitCreate(name="Bottle", code="BTL"))

    doc_user = await crud_user.get_user_by_email(db, "doc@test.com")
    med_in = MedicineCreate(
        name="Arnica",
        generic_name="Arnica",
        category_id=cat.id,
        manufacturer_id=man.id,
        potency_id=pot.id,
        unit_id=unit.id,
        purchase_price=100.0,
        selling_price=120.0,
        gst_percentage=5.0,
        is_active=True
    )
    med = await crud_medicine.create_medicine(db, med_in, doc_user.id)

    # 5. Inward stock at Gudivada (100 units)
    stock_in_gdv = {
        "medicine_id": str(med.id),
        "branch_id": str(gdv_branch.id),
        "batch_number": "B001",
        "purchase_price": 100.0,
        "selling_price": 120.0,
        "quantity": 100,
        "expiry_date": str(date.today() + timedelta(days=365)),
        "building": "Main",
        "room": "Room A"
    }
    tx_res = await client.post("/api/v1/inventory/stock-in", json=stock_in_gdv, headers=doc_headers)
    assert tx_res.status_code == 201
    batch_gdv_id = tx_res.json()["batch_id"]

    # 6. Inward stock at Kaikaluru (50 units)
    stock_in_kkl = stock_in_gdv.copy()
    stock_in_kkl["branch_id"] = str(kkl_branch.id)
    stock_in_kkl["quantity"] = 50
    tx_kkl_res = await client.post("/api/v1/inventory/stock-in", json=stock_in_kkl, headers=doc_headers)
    assert tx_kkl_res.status_code == 201

    # 7. Dispense 10 units at Gudivada
    dispense_gdv = {
        "batch_id": batch_gdv_id,
        "quantity": 10,
        "reason": "Sold"
    }
    disp_res = await client.post("/api/v1/inventory/dispense", json=dispense_gdv, headers=doc_headers)
    assert disp_res.status_code == 201

    # 8. Test System-wide stats (Doctor)
    stats_res = await client.get("/api/v1/dashboard/stats", headers=doc_headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()

    assert stats["total_medicines"] == 1
    assert stats["total_inventory_items"] == 140 # 90 at GDV + 50 at KKL
    assert stats["total_inventory_value"] == 14000.0 # 140 * 100.0
    assert stats["todays_stock_in"] == 150
    assert stats["todays_dispensed"] == 10

    # Branch-wise Statistics check
    b_stats = stats["branch_wise_stats"]
    assert len(b_stats) == 2
    # Verify Gudivada has 90 items and Kaikaluru has 50 items
    gdv_item = next(b for b in b_stats if b["branch_code"] == "GDV")
    assert gdv_item["total_inventory_items"] == 90
    assert gdv_item["total_inventory_value"] == 9000.0

    # Top Dispensed Medicines check
    top_disp = stats["top_dispensed_medicines"]
    assert len(top_disp) == 1
    assert top_disp[0]["name"] == "Arnica"
    assert top_disp[0]["value"] == 10

    # Recent Activity Timeline check
    assert len(stats["recent_activity"]) == 3 # Stock In, Stock In, Dispense

    # 9. Test Branch Filter stats (Doctor)
    stats_filter_res = await client.get(f"/api/v1/dashboard/stats?branch_id={gdv_branch.id}", headers=doc_headers)
    assert stats_filter_res.status_code == 200
    stats_filter = stats_filter_res.json()
    assert stats_filter["total_inventory_items"] == 90
    assert stats_filter["total_inventory_value"] == 9000.0
    assert len(stats_filter["branch_wise_stats"]) == 0 # Breakdown is empty when branch filter is active

    # 10. Test Assistant Stats Security Restriction
    # Assistant default branch is Kaikaluru (KKL) with 50 units.
    # Assistant tries to request system-wide, but API overrides to KKL default.
    asst_stats_res = await client.get("/api/v1/dashboard/stats", headers=asst_headers)
    assert asst_stats_res.status_code == 200
    asst_stats = asst_stats_res.json()
    assert asst_stats["total_inventory_items"] == 50
    assert asst_stats["total_inventory_value"] == 5000.0
