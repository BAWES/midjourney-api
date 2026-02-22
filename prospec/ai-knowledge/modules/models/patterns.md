# Patterns: models

<!-- prospec:auto-start -->

## SQLAlchemy 2.x Mapped Columns

All columns use the typed `Mapped[]` annotation:

```python
id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
name: Mapped[str] = mapped_column(String(255))
image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
```

## TimestampMixin

Applied to all models for automatic timestamp tracking:

```python
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

## Bidirectional Relationships

```python
# Parent side
tasks: Mapped[list["Task"]] = relationship(back_populates="api_key")

# Child side
api_key: Mapped["ApiKey"] = relationship(back_populates="tasks")
```

## Index Naming Convention

Pattern: `ix_{table}_{columns}` for indexes, `uq_{description}` for unique constraints:

```python
__table_args__ = (
    Index("ix_tasks_api_key_created", "api_key_id", "created_at"),
    UniqueConstraint("api_key_id", "usage_date", name="uq_api_key_date"),
)
```

## Pydantic ORM Mode

Schemas use `from_attributes=True` for direct ORM model conversion:

```python
class TaskResponse(BaseModel):
    model_config = {"from_attributes": True}
```

## Enum as Column Type

```python
status: Mapped[TaskStatus] = mapped_column(
    SQLEnum(TaskStatus), default=TaskStatus.QUEUED
)
```

<!-- prospec:auto-end -->

<!-- prospec:user-start -->
<!-- prospec:user-end -->
