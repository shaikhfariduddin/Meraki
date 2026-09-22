"""
User model.

Role is stored on the user row and is the single source of truth for
authorization — the backend never trusts a role claimed by the client.
The JWT carries a *copy* of the role for convenience, but every
sensitive check should ultimately trace back to this column.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    SELLER = "seller"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    # sqlalchemy.Uuid is dialect-agnostic: native UUID column on Postgres,
    # CHAR(32) on SQLite — same model works in prod and in tests.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.CUSTOMER, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
