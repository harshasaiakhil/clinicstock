from sqlalchemy import String, DateTime, ForeignKey, Integer, Date, Numeric, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID, uuid4
from datetime import datetime, date

from app.core.database import Base

class InventorySummary(Base):
    __tablename__ = "inventory_summaries"
    __table_args__ = (
        UniqueConstraint("medicine_id", "branch_id", name="uq_medicine_branch"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    medicine_id: Mapped[UUID] = mapped_column(ForeignKey("medicines.id"), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    total_quantity: Mapped[int] = mapped_column(Integer, default=0)
    available_quantity: Mapped[int] = mapped_column(Integer, default=0)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0)
    min_stock_level: Mapped[int] = mapped_column(Integer, default=5)
    max_stock_level: Mapped[int] = mapped_column(Integer, default=1000)
    reorder_level: Mapped[int] = mapped_column(Integer, default=10)

    # Default Location
    building: Mapped[str] = mapped_column(String(100), nullable=True)
    room: Mapped[str] = mapped_column(String(100), nullable=True)
    cupboard: Mapped[str] = mapped_column(String(100), nullable=True)
    rack: Mapped[str] = mapped_column(String(100), nullable=True)
    shelf: Mapped[str] = mapped_column(String(100), nullable=True)
    row: Mapped[str] = mapped_column(String(100), nullable=True)
    column: Mapped[str] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    medicine = relationship("Medicine", back_populates="inventories")
    branch = relationship("Branch", back_populates="inventories")
    batches = relationship("InventoryBatch", back_populates="summary", cascade="all, delete-orphan")

class InventoryBatch(Base):
    __tablename__ = "inventory_batches"
    __table_args__ = (
        UniqueConstraint("inventory_summary_id", "batch_number", name="uq_summary_batch_number"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    inventory_summary_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_summaries.id"), nullable=False)
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    selling_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0)

    # Batch-specific Location (if different from summary default)
    building: Mapped[str] = mapped_column(String(100), nullable=True)
    room: Mapped[str] = mapped_column(String(100), nullable=True)
    cupboard: Mapped[str] = mapped_column(String(100), nullable=True)
    rack: Mapped[str] = mapped_column(String(100), nullable=True)
    shelf: Mapped[str] = mapped_column(String(100), nullable=True)
    row: Mapped[str] = mapped_column(String(100), nullable=True)
    column: Mapped[str] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    summary = relationship("InventorySummary", back_populates="batches")
    supplier = relationship("Supplier")
    transactions = relationship("StockTransaction", back_populates="batch", cascade="all, delete-orphan")

class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_batches.id"), nullable=False)
    quantity_changed: Mapped[int] = mapped_column(Integer, nullable=False)  # positive for stock in, negative for out
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "Stock In", "Dispense", "Transfer Out", "Transfer In", "Adjustment", "Expired", "Damaged"
    reason: Mapped[str] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="stock_transactions")
    branch = relationship("Branch")
    batch = relationship("InventoryBatch", back_populates="transactions")
