import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TaskStatus, TimestampMixin


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_api_key_created", "api_key_id", "created_at"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_correlation_tag", "correlation_tag"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id")
    )
    prompt: Mapped[str] = mapped_column(Text)
    aspect_ratio: Mapped[str] = mapped_column(String(20), default="1:1")
    status: Mapped[TaskStatus] = mapped_column(default=TaskStatus.QUEUED)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_tag: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    api_key: Mapped["ApiKey"] = relationship(back_populates="tasks")
    usage_log: Mapped["UsageLog | None"] = relationship(back_populates="task")


class UsageLog(TimestampMixin, Base):
    __tablename__ = "usage_logs"
    __table_args__ = (
        Index("ix_usage_logs_api_key_created", "api_key_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), unique=True
    )
    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id")
    )
    prompt: Mapped[str] = mapped_column(Text)
    aspect_ratio: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    task: Mapped["Task"] = relationship(back_populates="usage_log")


# Avoid circular import
from app.models.api_key import ApiKey  # noqa: E402, F401
