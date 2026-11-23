from sqlalchemy import String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID, uuid4
from datetime import datetime
from app.core.database import Base

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)  # Null if system or failed auth
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., login, dispense, transfer
    details: Mapped[dict] = mapped_column(JSON, nullable=True)  # Contextual JSON metadata
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="activity_logs")
