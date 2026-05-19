"""MacroObservation — individual data points for a macroeconomic series."""

from __future__ import annotations

import uuid
from typing import Optional
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import CreatedAtMixin, JSONBType, UUIDPrimaryKeyMixin


class MacroObservation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One data point for a macroeconomic time series."""

    __tablename__ = "macro_observations"
    __table_args__ = (
        UniqueConstraint("macro_series_id", "observation_date",
                         name="uq_macro_obs_series_date"),
        Index("ix_macro_obs_date", "observation_date"),
    )

    macro_series_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("macro_series.id", ondelete="CASCADE"), nullable=False
    )
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    observation_value: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
