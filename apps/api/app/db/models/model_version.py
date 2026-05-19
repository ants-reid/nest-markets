from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from typing import Optional


class ModelVersion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Versioned model/provider configuration."""

    __tablename__ = "model_versions"

    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    alias_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(nullable=True)
    top_p: Mapped[Optional[float]] = mapped_column(nullable=True)
    max_output_tokens: Mapped[Optional[int]] = mapped_column(nullable=True)
    reasoning_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    supports_structured_output: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
