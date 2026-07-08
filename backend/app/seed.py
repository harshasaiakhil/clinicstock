import asyncio
from app.core.database import AsyncSessionLocal
from app.crud import branch as crud_branch
from app.crud import user as crud_user
from app.crud import medicine_unit as crud_unit
from app.crud import potency as crud_potency
from app.schemas.branch import BranchCreate
from app.schemas.user import UserCreate
from app.schemas.medicine_unit import MedicineUnitCreate
from app.schemas.potency import PotencyCreate

async def seed_data():
    async with AsyncSessionLocal() as db:
        print("Seeding database...")

        # 1. Seed branches
        gdv_branch = await crud_branch.get_branch_by_code(db, "GDV")
        if not gdv_branch:
            print("Creating Gudivada branch...")
            gdv_branch = await crud_branch.create_branch(
                db,
                BranchCreate(
                    name="Gudivada",
                    code="GDV",
                    address="Gudivada Branch Address",
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
                    address="Kaikaluru Branch Address",
                    phone="8888888888"
                )
            )
        else:
            print("Kaikaluru branch already exists.")

        # 2. Seed Users
        doctor = await crud_user.get_user_by_email(db, "doctor@clinicstock.com")
        if not doctor:
            print("Creating default Doctor user...")
            await crud_user.create_user(
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
            print("Creating default Assistant user...")
            await crud_user.create_user(
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
        for name, code in units_to_seed:
            existing = await crud_unit.get_medicine_unit_by_code(db, code)
            if not existing:
                print(f"Creating unit: {name} ({code})...")
                await crud_unit.create_medicine_unit(db, MedicineUnitCreate(name=name, code=code))

        # 4. Seed Potencies
        potencies_to_seed = ["Q", "30C", "200C", "1M", "10M", "50M", "CM", "3X", "6X", "12X"]
        for name in potencies_to_seed:
            existing = await crud_potency.get_potency_by_name(db, name)
            if not existing:
                print(f"Creating potency: {name}...")
                await crud_potency.create_potency(db, PotencyCreate(name=name))

        print("Seeding finished successfully.")

if __name__ == "__main__":
    asyncio.run(seed_data())
