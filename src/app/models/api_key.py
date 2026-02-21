import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ApiKey(TimestampMixin, Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    daily_limit: Mapped[int] = mapped_column(Integer, default=50)
    monthly_limit: Mapped[int] = mapped_column(Integer, default=1000)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    tasks: Mapped[list["Task"]] = relationship(back_populates="api_key")
    quota_usages: Mapped[list["QuotaUsage"]] = relationship(back_populates="api_key")


class QuotaUsage(TimestampMixin, Base):
    __tablename__ = "quota_usages"
    __table_args__ = (
        UniqueConstraint("api_key_id", "usage_date", name="uq_api_key_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id"), index=True
    )
    usage_date: Mapped[date] = mapped_column(Date, index=True)
    daily_used: Mapped[int] = mapped_column(Integer, default=0)

    api_key: Mapped["ApiKey"] = relationship(back_populates="quota_usages")


# Avoid circular import: Task is defined in task.py but referenced here
from app.models.task import Task  # noqa: E402, F401
