from sqlalchemy import String, DateTime, ForeignKey, Integer, Date, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID, uuid4
from datetime import datetime, date
from app.core.database import Base

class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    medicine_id: Mapped[UUID] = mapped_column(ForeignKey("medicines.id"), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    min_stock_level: Mapped[int] = mapped_column(Integer, default=5)

    # Location details
    building: Mapped[str] = mapped_column(String(100), nullable=True)
    room: Mapped[str] = mapped_column(String(100), nullable=True)
    cupboard: Mapped[str] = mapped_column(String(100), nullable=True)
    rack: Mapped[str] = mapped_column(String(100), nullable=True)
    shelf: Mapped[str] = mapped_column(String(100), nullable=True)

    # Batch Details
    batch_number: Mapped[str] = mapped_column(String(100), nullable=True)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    medicine = relationship("Medicine", back_populates="inventories")
    branch = relationship("Branch", back_populates="inventories")

class StockHistory(Base):
    __tablename__ = "stock_history"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    medicine_id: Mapped[UUID] = mapped_column(ForeignKey("medicines.id"), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)

    from_branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=True)
    to_branch_id: Mapped[UUID] = mapped_column(ForeignKey("branches.id"), nullable=True)

    quantity_changed: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_type: Mapped[str] = mapped_column(String(50), nullable=False)  # add | dispense | transfer | adjustment | purchase
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    notes: Mapped[str] = mapped_column(String(255), nullable=True)

    # Sync fields
    sync_status: Mapped[str] = mapped_column(String(20), default="synced")  # pending | synced | failed
    client_tx_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    medicine = relationship("Medicine", back_populates="stock_histories")
    user = relationship("User", back_populates="stock_histories")
