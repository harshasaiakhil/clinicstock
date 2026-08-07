import io
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import Tuple, List, Dict
import math

from app.models.medicine import Category, Manufacturer, Potency, MedicineUnit, Medicine
from app.crud import medicine as crud_medicine
from app.schemas.medicine import MedicineCreate, MedicineUpdate, MedicineImportSummary

async def get_master_data_lookups(
    db: AsyncSession
) -> Tuple[Dict[str, UUID], Dict[str, UUID], Dict[str, UUID], Dict[str, UUID]]:
    # Fetch all categories
    cat_res = await db.execute(select(Category).where(Category.is_deleted == False))
    categories = {c.name.strip().lower(): c.id for c in cat_res.scalars().all()}

    # Fetch all manufacturers
    man_res = await db.execute(select(Manufacturer).where(Manufacturer.is_deleted == False))
    manufacturers = {m.name.strip().lower(): m.id for m in man_res.scalars().all()}

    # Fetch all potencies
    pot_res = await db.execute(select(Potency).where(Potency.is_deleted == False))
    potencies = {p.name.strip().lower(): p.id for p in pot_res.scalars().all()}

    # Fetch all units
    unit_res = await db.execute(select(MedicineUnit).where(MedicineUnit.is_deleted == False))
    units = {}
    for u in unit_res.scalars().all():
        units[u.name.strip().lower()] = u.id
        units[u.code.strip().lower()] = u.id

    return categories, manufacturers, potencies, units

def sanitize_value(val):
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    return str(val).strip()

async def import_medicines_from_dataframe(
    db: AsyncSession, df: pd.DataFrame, user_id: UUID
) -> MedicineImportSummary:
    summary = MedicineImportSummary()

    # Fetch lookups
    categories, manufacturers, potencies, units = await get_master_data_lookups(db)

    # Keep track of unique key combinations processed in this import run
    seen_in_import = set()

    for index, row in df.iterrows():
        row_num = index + 1
        try:
            name = sanitize_value(row.get("Name"))
            generic_name = sanitize_value(row.get("Generic Name"))
            cat_name = sanitize_value(row.get("Category"))
            man_name = sanitize_value(row.get("Manufacturer"))
            pot_name = sanitize_value(row.get("Potency"))
            unit_name = sanitize_value(row.get("Unit"))

            # Numeric values
            try:
                quantity = int(row.get("Quantity", 0))
                selling_price = float(row.get("Selling Price", 0.0))
                gst_percentage = float(row.get("GST Percentage", 0.0))
            except (ValueError, TypeError):
                summary.failed += 1
                summary.errors.append(f"Row {row_num}: Invalid numeric values.")
                continue

            hsn_code = sanitize_value(row.get("HSN Code"))
            description = sanitize_value(row.get("Description"))
            barcode = sanitize_value(row.get("Barcode"))
            qr_code = sanitize_value(row.get("QR Code"))

            cupboard = sanitize_value(row.get("Cupboard"))
            rack = sanitize_value(row.get("Rack"))
            row_val = sanitize_value(row.get("Row"))
            column_val = sanitize_value(row.get("Column"))

            # Active status
            is_active_val = row.get("Active", True)
            if isinstance(is_active_val, str):
                is_active = is_active_val.lower() in ("true", "1", "yes", "active")
            else:
                is_active = bool(is_active_val)

            # Basic validation
            if not name:
                summary.failed += 1
                summary.errors.append(f"Row {row_num}: Medicine name is required.")
                continue

            if quantity < 0 or selling_price < 0 or gst_percentage < 0:
                summary.failed += 1
                summary.errors.append(f"Row {row_num}: Quantity, prices or GST cannot be negative.")
                continue

            # Look up foreign keys
            cat_id = categories.get(cat_name.lower()) if cat_name else None
            man_id = manufacturers.get(man_name.lower()) if man_name else None
            pot_id = potencies.get(pot_name.lower()) if pot_name else None
            unit_id = units.get(unit_name.lower()) if unit_name else None

            # Manufacturer is optional, but if specified it must exist
            man_failed = False
            if man_name and not man_id:
                man_failed = True

            if not cat_id or man_failed or not pot_id or not unit_id:
                missing = []
                if not cat_id:
                    missing.append(f"Category '{cat_name}'")
                if man_failed:
                    missing.append(f"Manufacturer '{man_name}'")
                if not pot_id:
                    missing.append(f"Potency '{pot_name}'")
                if not unit_id:
                    missing.append(f"Unit '{unit_name}'")
                summary.failed += 1
                summary.errors.append(
                    f"Row {row_num}: Foreign keys not found: {', '.join(missing)}."
                )
                continue

            # Check unique constraint (Name + Manufacturer + Potency)
            unique_key = (name.lower(), man_id, pot_id)
            if unique_key in seen_in_import:
                summary.duplicate_rows += 1
                summary.errors.append(f"Row {row_num}: Duplicate row in the imported file.")
                continue
            seen_in_import.add(unique_key)

            # Check if exists in database
            existing = await crud_medicine.get_medicine_by_unique_key(
                db, name, man_id, pot_id
            )
            if existing:
                # Update existing medicine
                med_update = MedicineUpdate(
                    generic_name=generic_name,
                    category_id=cat_id,
                    unit_id=unit_id,
                    quantity=quantity,
                    selling_price=selling_price,
                    gst_percentage=gst_percentage,
                    hsn_code=hsn_code,
                    description=description,
                    barcode=barcode,
                    qr_code=qr_code,
                    is_active=is_active,
                )
                await crud_medicine.update_medicine(db, existing.id, med_update, user_id)
                summary.updated += 1
            else:
                # Create new medicine
                med_create = MedicineCreate(
                    name=name,
                    generic_name=generic_name,
                    category_id=cat_id,
                    manufacturer_id=man_id,
                    potency_id=pot_id,
                    unit_id=unit_id,
                    quantity=quantity,
                    selling_price=selling_price,
                    gst_percentage=gst_percentage,
                    hsn_code=hsn_code,
                    description=description,
                    barcode=barcode,
                    qr_code=qr_code,
                    is_active=is_active,
                )
                await crud_medicine.create_medicine(db, med_create, user_id)
                summary.imported += 1

            # Get medicine object
            db_med = existing
            if not db_med:
                db_med = await crud_medicine.get_medicine_by_unique_key(db, name, man_id, pot_id)

            if db_med and (cupboard or rack or row_val or column_val):
                from app.models.user import User
                from app.models.inventory import InventorySummary
                user_obj = await db.get(User, user_id)
                branch_id = user_obj.default_branch_id if user_obj else None
                if branch_id:
                    from sqlalchemy import select
                    stmt = select(InventorySummary).where(
                        InventorySummary.medicine_id == db_med.id,
                        InventorySummary.branch_id == branch_id
                    )
                    res = await db.execute(stmt)
                    inv_sum = res.scalars().first()
                    if not inv_sum:
                        inv_sum = InventorySummary(
                            medicine_id=db_med.id,
                            branch_id=branch_id,
                            total_quantity=0,
                            available_quantity=0,
                            reserved_quantity=0,
                            cupboard=cupboard,
                            rack=rack,
                            row=row_val,
                            column=column_val
                        )
                        db.add(inv_sum)
                    else:
                        inv_sum.cupboard = cupboard
                        inv_sum.rack = rack
                        inv_sum.row = row_val
                        inv_sum.column = column_val
                    await db.flush()

        except Exception as e:
            summary.failed += 1
            summary.errors.append(f"Row {row_num}: Unexpected error: {str(e)}")

    return summary

async def parse_csv_import(
    db: AsyncSession, file_bytes: bytes, user_id: UUID
) -> MedicineImportSummary:
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
        return await import_medicines_from_dataframe(db, df, user_id)
    except Exception as e:
        summary = MedicineImportSummary()
        summary.failed = 1
        summary.errors.append(f"Failed to parse CSV file: {str(e)}")
        return summary

async def parse_excel_import(
    db: AsyncSession, file_bytes: bytes, user_id: UUID
) -> MedicineImportSummary:
    try:
        df = pd.read_excel(io.BytesIO(file_bytes))
        return await import_medicines_from_dataframe(db, df, user_id)
    except Exception as e:
        summary = MedicineImportSummary()
        summary.failed = 1
        summary.errors.append(f"Failed to parse Excel file: {str(e)}")
        return summary

async def generate_export_dataframe(db: AsyncSession, branch_id: Optional[UUID] = None) -> pd.DataFrame:
    medicines = await crud_medicine.get_medicines(db, limit=100000)  # get all
    data = []
    for m in medicines:
        if branch_id:
            inv = next((i for i in m.inventories if i.branch_id == branch_id), None)
            if not inv:
                continue
        else:
            inv = m.inventories[0] if m.inventories else None

        data.append(
            {
                "Name": m.name,
                "Generic Name": m.generic_name or "",
                "Category": m.category.name if m.category else "",
                "Manufacturer": m.manufacturer.name if m.manufacturer else "",
                "Potency": m.potency.name if m.potency else "",
                "Unit": m.unit.name if m.unit else "",
                "Quantity": inv.total_quantity if (branch_id and inv) else m.quantity,
                "Selling Price": m.selling_price,
                "GST Percentage": m.gst_percentage,
                "HSN Code": m.hsn_code or "",
                "Description": m.description or "",
                "Barcode": m.barcode or "",
                "QR Code": m.qr_code or "",
                "Active": m.is_active,
                "Cupboard": inv.cupboard if inv else "",
                "Rack": inv.rack if inv else "",
                "Row": inv.row if inv else "",
                "Column": inv.column if inv else "",
            }
        )
    return pd.DataFrame(data)

async def generate_csv_export(db: AsyncSession, branch_id: Optional[UUID] = None) -> bytes:
    df = await generate_export_dataframe(db, branch_id=branch_id)
    csv_str = df.to_csv(index=False)
    return csv_str.encode("utf-8")

async def generate_excel_export(db: AsyncSession, branch_id: Optional[UUID] = None) -> bytes:
    df = await generate_export_dataframe(db, branch_id=branch_id)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Medicines")
    return output.getvalue()
