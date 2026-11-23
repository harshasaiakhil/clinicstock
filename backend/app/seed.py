import asyncio
from datetime import date, timedelta
from app.core.database import AsyncSessionLocal
from app.crud import branch as crud_branch
from app.crud import user as crud_user
from app.crud import medicine_unit as crud_unit
from app.crud import potency as crud_potency
from app.crud import category as crud_category
from app.crud import manufacturer as crud_manufacturer
from app.crud import supplier as crud_supplier
from app.crud import medicine as crud_medicine
from app.services import inventory as service_inventory

from app.schemas.branch import BranchCreate
from app.schemas.user import UserCreate
from app.schemas.medicine_unit import MedicineUnitCreate
from app.schemas.potency import PotencyCreate
from app.schemas.category import CategoryCreate
from app.schemas.manufacturer import ManufacturerCreate
from app.schemas.supplier import SupplierCreate
from app.schemas.medicine import MedicineCreate
from app.schemas.inventory import StockInPayload

async def seed_data():
    async with AsyncSessionLocal() as db:
        print("Explicit database seeding in progress...")

        # 1. Seed branches
        gdv_branch = await crud_branch.get_branch_by_code(db, "GDV")
        if not gdv_branch:
            print("Creating Gudivada branch...")
            gdv_branch = await crud_branch.create_branch(
                db,
                BranchCreate(
                    name="Gudivada",
                    code="GDV",
                    address="Gudivada Main Road",
                    phone="9999999999"
                )
            )
        else:
            print("Gudivada branch already exists.")

        kkl_branch = await crud_branch.get_branch_by_code(db, "KKL")
        if not kkl_branch:
            print("Creating Kaikaluru branch...")
            kkl_branch = await crud_branch.create_branch(
                db,
                BranchCreate(
                    name="Kaikaluru",
                    code="KKL",
                    address="Kaikaluru Clinic Center",
                    phone="8888888888"
                )
            )
        else:
            print("Kaikaluru branch already exists.")

        # 2. Seed Users
        doctor = await crud_user.get_user_by_email(db, "doctor@clinicstock.com")
        if not doctor:
            print("Creating default Doctor user (doctor@clinicstock.com)...")
            doctor = await crud_user.create_user(
                db,
                UserCreate(
                    email="doctor@clinicstock.com",
                    password="Password123",
                    first_name="Admin",
                    last_name="Doctor",
                    role="doctor",
                    default_branch_id=gdv_branch.id
                )
            )
        else:
            print("Doctor user already exists.")

        assistant = await crud_user.get_user_by_email(db, "assistant@clinicstock.com")
        if not assistant:
            print("Creating default Assistant user (assistant@clinicstock.com)...")
            assistant = await crud_user.create_user(
                db,
                UserCreate(
                    email="assistant@clinicstock.com",
                    password="Password123",
                    first_name="Clinic",
                    last_name="Assistant",
                    role="assistant",
                    default_branch_id=kkl_branch.id
                )
            )
        else:
            print("Assistant user already exists.")

        # 3. Seed Medicine Units
        units_to_seed = [
            ("Bottle", "BTL"),
            ("Tube", "TUB"),
            ("Box", "BOX"),
            ("Pack", "PCK"),
            ("Strip", "STP"),
            ("Piece", "PCS"),
        ]
        created_units = {}
        for name, code in units_to_seed:
            existing = await crud_unit.get_medicine_unit_by_code(db, code)
            if not existing:
                print(f"Creating unit: {name} ({code})...")
                existing = await crud_unit.create_medicine_unit(db, MedicineUnitCreate(name=name, code=code))
            created_units[code] = existing

        # 4. Seed Potencies
        potencies_to_seed = ["Q", "30C", "200C", "1M", "10M", "50M", "CM", "3X", "6X", "12X"]
        created_potencies = {}
        for name in potencies_to_seed:
            existing = await crud_potency.get_potency_by_name(db, name)
            if not existing:
                print(f"Creating potency: {name}...")
                existing = await crud_potency.create_potency(db, PotencyCreate(name=name))
            created_potencies[name] = existing

        # 5. Seed Categories
        categories_to_seed = [
            "Mother Tincture",
            "💧 Dilution",
            "⚪ Biochemic Tablet",
            "💊 Pills / Globules",
            "🧴 Ointment",
            "💧 Drops",
            "🧪 Syrup",
            "🌾 Powder",
            "🩹 External Application",
            "⭐ Specialty Medicine",
            "📦 Others",
        ]
        created_categories = {}
        for name in categories_to_seed:
            existing = await crud_category.get_category_by_name(db, name)
            if not existing:
                safe_name = name.encode('ascii', 'ignore').decode().strip() or name
                print(f"Creating category: {safe_name}...")
                existing = await crud_category.create_category(db, CategoryCreate(name=name))
            created_categories[name] = existing

        # 6. Seed Manufacturers
        manufacturers_to_seed = ["Dr. Reckeweg", "SBL Pvt Ltd", "Schwabe India"]
        created_manufacturers = {}
        for name in manufacturers_to_seed:
            existing = await crud_manufacturer.get_manufacturer_by_name(db, name)
            if not existing:
                print(f"Creating manufacturer: {name}...")
                existing = await crud_manufacturer.create_manufacturer(db, ManufacturerCreate(name=name))
            created_manufacturers[name] = existing

        # 7. Seed Suppliers
        suppliers_to_seed = [
            ("Standard Homeo Distributors", "std@homeo.com", "9876543210"),
            ("Apex Pharma Supplies", "apex@pharma.com", "9123456780"),
        ]
        created_suppliers = {}
        for name, email, phone in suppliers_to_seed:
            existing = await crud_supplier.get_supplier_by_name(db, name)
            if not existing:
                print(f"Creating supplier: {name}...")
                existing = await crud_supplier.create_supplier(
                    db, SupplierCreate(name=name, email=email, phone=phone)
                )
            created_suppliers[name] = existing

        # 8. Seed Initial Sample Medicines & Stock (if no medicines exist)
        med_check = await crud_medicine.get_medicines(db, limit=1)
        if not med_check:
            print("Creating sample catalog medicines & batches...")
            sample_meds = [
                {
                    "name": "Arnica Montana",
                    "generic_name": "Mountain Daisy",
                    "category": "💧 Dilution",
                    "manufacturer": "Dr. Reckeweg",
                    "potency": "200C",
                    "unit": "BTL",
                    "selling_price": 240.0,
                    "batches": [
                        {
                            "branch": gdv_branch,
                            "batch_number": "ARN-GDV-01",
                            "quantity": 30,
                            "purchase_price": 180.0,
                            "selling_price": 240.0,
                            "expiry_date": date.today() + timedelta(days=365),
                            "cupboard": "C-01",
                            "rack": "R-01",
                            "row": "Row 01",
                            "column": "Col 01",
                        },
                        {
                            "branch": kkl_branch,
                            "batch_number": "ARN-KKL-01",
                            "quantity": 15,
                            "purchase_price": 180.0,
                            "selling_price": 240.0,
                            "expiry_date": date.today() + timedelta(days=365),
                            "cupboard": "C-02",
                            "rack": "R-01",
                            "row": "Row 02",
                            "column": "Col 01",
                        },
                    ]
                },
                {
                    "name": "Belladonna",
                    "generic_name": "Deadly Nightshade",
                    "category": "💧 Dilution",
                    "manufacturer": "SBL Pvt Ltd",
                    "potency": "30C",
                    "unit": "BTL",
                    "selling_price": 120.0,
                    "batches": [
                        {
                            "branch": gdv_branch,
                            "batch_number": "BEL-GDV-01",
                            "quantity": 25,
                            "purchase_price": 85.0,
                            "selling_price": 120.0,
                            "expiry_date": date.today() + timedelta(days=400),
                            "cupboard": "C-01",
                            "rack": "R-02",
                            "row": "Row 01",
                            "column": "Col 02",
                        }
                    ]
                },
                {
                    "name": "Calcarea Carbonica",
                    "generic_name": "Oyster Shell",
                    "category": "⚪ Biochemic Tablet",
                    "manufacturer": "Schwabe India",
                    "potency": "6X",
                    "unit": "BOX",
                    "selling_price": 160.0,
                    "batches": [
                        {
                            "branch": kkl_branch,
                            "batch_number": "CAL-KKL-01",
                            "quantity": 10,
                            "purchase_price": 110.0,
                            "selling_price": 160.0,
                            "expiry_date": date.today() + timedelta(days=250),
                            "cupboard": "C-03",
                            "rack": "R-01",
                            "row": "Row 01",
                            "column": "Col 01",
                        }
                    ]
                },
            ]

            default_supplier = list(created_suppliers.values())[0] if created_suppliers else None

            for m in sample_meds:
                cat = created_categories.get(m["category"])
                mfr = created_manufacturers.get(m["manufacturer"])
                pot = created_potencies.get(m["potency"])
                un = created_units.get(m["unit"])

                med = await crud_medicine.create_medicine(
                    db,
                    MedicineCreate(
                        name=m["name"],
                        generic_name=m["generic_name"],
                        category_id=cat.id,
                        manufacturer_id=mfr.id if mfr else None,
                        potency_id=pot.id,
                        unit_id=un.id,
                        quantity=sum(b["quantity"] for b in m["batches"]),
                        selling_price=m["selling_price"],
                        gst_percentage=5.0,
                        is_active=True,
                    ),
                    user_id=doctor.id,
                )

                for b in m["batches"]:
                    await service_inventory.perform_stock_in(
                        db,
                        StockInPayload(
                            medicine_id=med.id,
                            branch_id=b["branch"].id,
                            batch_number=b["batch_number"],
                            supplier_id=default_supplier.id if default_supplier else None,
                            purchase_date=date.today(),
                            expiry_date=b["expiry_date"],
                            purchase_price=b["purchase_price"],
                            selling_price=b["selling_price"],
                            quantity=b["quantity"],
                            cupboard=b.get("cupboard"),
                            rack=b.get("rack"),
                            row=b.get("row"),
                            column=b.get("column"),
                            reason="Initial system seed",
                        ),
                        user_id=doctor.id,
                    )

        print("Seeding finished successfully.")

if __name__ == "__main__":
    asyncio.run(seed_data())
