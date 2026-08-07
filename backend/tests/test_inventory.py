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

async def test_inventory_management_flow(client: AsyncClient, db: AsyncSession):
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

    # 4. Seed Masters
    cat = await crud_category.create_category(db, CategoryCreate(name="Dilutions"))
    man = await crud_manufacturer.create_manufacturer(db, ManufacturerCreate(name="SBL"))
    pot = await crud_potency.create_potency(db, PotencyCreate(name="30C"))
    unit = await crud_unit.create_medicine_unit(db, MedicineUnitCreate(name="Bottle", code="BTL"))

    # Seed Doctor user id for audits
    doc_user = await crud_user.get_user_by_email(db, "doc@test.com")

    # Seed Medicine
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

    # --- Test 1: Stock In (Doctor, Success) ---
    stock_in_payload = {
        "medicine_id": str(med.id),
        "branch_id": str(gdv_branch.id),
        "batch_number": "BATCH001",
        "purchase_price": 100.0,
        "selling_price": 120.0,
        "quantity": 100,
        "expiry_date": str(date.today() + timedelta(days=365)),
        "building": "Main",
        "room": "Room A",
        "cupboard": "C1",
        "rack": "R2",
        "shelf": "S3",
        "reason": "Initial stock inwarding"
    }
    tx_res = await client.post("/api/v1/inventory/stock-in", json=stock_in_payload, headers=doc_headers)
    assert tx_res.status_code == 201
    tx_data = tx_res.json()
    assert tx_data["quantity_changed"] == 100
    assert tx_data["transaction_type"] == "Stock In"
    batch_id = tx_data["batch_id"]

    # Verify Summary quantities
    summaries_res = await client.get(f"/api/v1/inventory/summaries?branch_id={gdv_branch.id}", headers=asst_headers)
    assert summaries_res.status_code == 200
    summaries = summaries_res.json()
    assert len(summaries) == 1
    assert summaries[0]["total_quantity"] == 100
    assert summaries[0]["available_quantity"] == 100
    assert summaries[0]["building"] == "Main"
    summary_id = summaries[0]["id"]

    # Verify Batch quantity
    batches_res = await client.get(f"/api/v1/inventory/batches?summary_id={summary_id}", headers=asst_headers)
    assert batches_res.status_code == 200
    batches = batches_res.json()
    assert len(batches) == 1
    assert batches[0]["quantity"] == 100
    assert batches[0]["batch_number"] == "BATCH001"

    # --- Test 2: Assistant Role Restriction on Stock In (Fail) ---
    tx_fail = await client.post("/api/v1/inventory/stock-in", json=stock_in_payload, headers=asst_headers)
    assert tx_fail.status_code == 403

    # --- Test 3: Dispense (Assistant, Success) ---
    dispense_payload = {
        "batch_id": batch_id,
        "quantity": 10,
        "reason": "Dispensed to patient"
    }
    disp_res = await client.post("/api/v1/inventory/dispense", json=dispense_payload, headers=asst_headers)
    assert disp_res.status_code == 201
    assert disp_res.json()["quantity_changed"] == -10
    assert disp_res.json()["transaction_type"] == "Dispense"

    # Check that quantities decremented
    summary_after = await client.get(f"/api/v1/inventory/summaries/{summary_id}", headers=asst_headers)
    assert summary_after.json()["available_quantity"] == 90
    assert summary_after.json()["total_quantity"] == 90

    # --- Test 4: Dispense Expiry Validation (Fail) ---
    # Stock In an expired batch first
    expired_stock_in = stock_in_payload.copy()
    expired_stock_in["batch_number"] = "EXPIRED001"
    expired_stock_in["expiry_date"] = str(date.today() - timedelta(days=10)) # expired 10 days ago
    expired_tx = await client.post("/api/v1/inventory/stock-in", json=expired_stock_in, headers=doc_headers)
    assert expired_tx.status_code == 201
    expired_batch_id = expired_tx.json()["batch_id"]

    # Attempt to dispense from expired batch
    disp_expired_payload = {
        "batch_id": expired_batch_id,
        "quantity": 5,
        "reason": "Dispensing expired batch"
    }
    disp_exp_res = await client.post("/api/v1/inventory/dispense", json=disp_expired_payload, headers=asst_headers)
    assert disp_exp_res.status_code == 400
    assert "expired" in disp_exp_res.json()["detail"].lower()

    # --- Test 5: Transfer Stock (Doctor, Success) ---
    transfer_payload = {
        "batch_id": batch_id,
        "to_branch_id": str(kkl_branch.id),
        "quantity": 20,
        "reason": "Transfer to Kaikaluru branch"
    }
    trans_res = await client.post("/api/v1/inventory/transfer", json=transfer_payload, headers=doc_headers)
    assert trans_res.status_code == 201
    trans_txs = trans_res.json()
    assert len(trans_txs) == 2
    # Transfer Out Transaction
    assert trans_txs[0]["quantity_changed"] == -20
    assert trans_txs[0]["transaction_type"] == "Transfer Out"
    # Transfer In Transaction
    assert trans_txs[1]["quantity_changed"] == 20
    assert trans_txs[1]["transaction_type"] == "Transfer In"

    # Verify Gudivada quantites reduced (90 - 20 = 70 for BATCH001; total is 170 including EXPIRED001)
    gdv_summary = await client.get(f"/api/v1/inventory/summaries/{summary_id}", headers=asst_headers)
    assert gdv_summary.json()["available_quantity"] == 170

    # Verify BATCH001 quantity is 70
    gdv_batch_btl = await client.get(f"/api/v1/inventory/batches/{batch_id}", headers=asst_headers)
    assert gdv_batch_btl.json()["quantity"] == 70

    # Verify Kaikaluru summaries created & updated
    kkl_summaries = await client.get(f"/api/v1/inventory/summaries?branch_id={kkl_branch.id}", headers=asst_headers)
    assert kkl_summaries.status_code == 200
    assert len(kkl_summaries.json()) == 1
    assert kkl_summaries.json()[0]["available_quantity"] == 20

    # --- Test 6: Stock Adjustment (Doctor, Success) ---
    adjust_payload = {
        "batch_id": batch_id,
        "quantity_changed": -5,
        "transaction_type": "Adjustment",
        "reason": "Spillage damage adjustment"
    }
    adj_res = await client.post("/api/v1/inventory/adjust", json=adjust_payload, headers=doc_headers)
    assert adj_res.status_code == 201
    assert adj_res.json()["quantity_changed"] == -5
    assert adj_res.json()["transaction_type"] == "Adjustment"

    # Verify final quantity (170 - 5 = 165)
    gdv_summary_final = await client.get(f"/api/v1/inventory/summaries/{summary_id}", headers=asst_headers)
    assert gdv_summary_final.json()["available_quantity"] == 165

    # Verify BATCH001 quantity is 65
    gdv_batch_btl_final = await client.get(f"/api/v1/inventory/batches/{batch_id}", headers=asst_headers)
    assert gdv_batch_btl_final.json()["quantity"] == 65

    # --- Test 7: Low Stock Filter ---
    # Default reorder_level=10, stock=165 -> low stock check (false) should return 0 results
    low_stock_res = await client.get("/api/v1/inventory/summaries?is_low_stock=true", headers=asst_headers)
    assert len(low_stock_res.json()) == 0

    # Update summary reorder_level=200 -> low stock check (true) should return 1 result (Gudivada, as 165 <= 200)
    await client.put(f"/api/v1/inventory/summaries/{summary_id}", json={"reorder_level": 200}, headers=doc_headers)
    low_stock_res_after = await client.get("/api/v1/inventory/summaries?is_low_stock=true", headers=asst_headers)
    assert len(low_stock_res_after.json()) == 1
    assert low_stock_res_after.json()[0]["id"] == str(summary_id)

    # --- Test 8: Stock Transaction Audit History Log ---
    tx_history = await client.get("/api/v1/inventory/transactions", headers=asst_headers)
    assert tx_history.status_code == 200
    txs = tx_history.json()
    # Check that transaction audit logs exist
    assert len(txs) >= 5 # Stock In, Dispense, Stock In (expired), Transfer Out, Transfer In, Adjustment
    # Verify all transaction types are logged in audit history
    types = [tx["transaction_type"] for tx in txs]
    assert "Adjustment" in types
    assert "Dispense" in types
    assert "Stock In" in types
    assert "Transfer Out" in types
    assert "Transfer In" in types
