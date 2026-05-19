from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import ExecutionModeName
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class ExecutionMode(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Available execution mode records."""

    __tablename__ = "execution_modes"

    name: Mapped[ExecutionModeName] = mapped_column(Enum(ExecutionModeName, name="execution_mode_name_enum"), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    requires_approval: Mapped[str] = mapped_column(String(20), nullable=False, default="inactive", server_default="inactive")
    allows_live_orders: Mapped[str] = mapped_column(String(20), nullable=False, default="inactive", server_default="inactive")
