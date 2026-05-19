"""MacroSeries — metadata for economic time series (CPI, yields, VIX, etc.)."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from typing import Optional


class MacroSeries(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Metadata for a macroeconomic data series."""

    __tablename__ = "macro_series"

    series_code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    series_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    units: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    frequency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
