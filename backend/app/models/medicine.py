from sqlalchemy import String, Boolean, DateTime, ForeignKey, Numeric, UniqueConstraint, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID, uuid4
from datetime import datetime

from app.core.database import Base

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    medicines = relationship("Medicine", back_populates="category")

class Manufacturer(Base):
    __tablename__ = "manufacturers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    medicines = relationship("Medicine", back_populates="manufacturer")

class MedicineUnit(Base):
    __tablename__ = "medicine_units"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)  # e.g., BTL, TUB, BOX
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    medicines = relationship("Medicine", back_populates="unit")

class Potency(Base):
    __tablename__ = "potencies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # e.g., 30C, 200C, Q
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    medicines = relationship("Medicine", back_populates="potency")

class Medicine(Base):
    __tablename__ = "medicines"
    __table_args__ = (
        UniqueConstraint(
            "name", "manufacturer_id", "potency_id",
            name="uq_medicine_name_manufacturer_potency"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    generic_name: Mapped[str] = mapped_column(String(150), nullable=True, index=True)
    
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"), nullable=False, index=True)
    manufacturer_id: Mapped[UUID] = mapped_column(ForeignKey("manufacturers.id"), nullable=True)
    potency_id: Mapped[UUID] = mapped_column(ForeignKey("potencies.id"), nullable=False)
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("medicine_units.id"), nullable=False)
    
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    selling_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    gst_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    hsn_code: Mapped[str] = mapped_column(String(20), nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    image_url: Mapped[str] = mapped_column(String(255), nullable=True)
    barcode: Mapped[str] = mapped_column(String(50), nullable=True)
    qr_code: Mapped[str] = mapped_column(String(100), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Relationships
    category = relationship("Category", back_populates="medicines")
    manufacturer = relationship("Manufacturer", back_populates="medicines")
    unit = relationship("MedicineUnit", back_populates="medicines")
    potency = relationship("Potency", back_populates="medicines")
    inventories = relationship("InventorySummary", back_populates="medicine")
    purchase_order_items = relationship("PurchaseOrderItem", back_populates="medicine")
    
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])
