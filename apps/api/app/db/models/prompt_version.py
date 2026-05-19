from sqlalchemy import Boolean, Enum, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import PromptRole
from app.db.models.mixins import JSONBType, CreatedAtMixin, UUIDPrimaryKeyMixin
from typing import Optional


class PromptVersion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Versioned prompt definitions."""

    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("role", "version", name="uq_prompt_versions_role_version"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[PromptRole] = mapped_column(Enum(PromptRole, name="prompt_role_enum"), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_template: Mapped[str] = mapped_column(Text, nullable=False)
    schema_json: Mapped[dict] = mapped_column(JSONBType, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
