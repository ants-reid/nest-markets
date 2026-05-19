from sqlalchemy import BigInteger, Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import AssetClass
from app.db.models.mixins import JSONBType, TimestampMixin, UUIDPrimaryKeyMixin
from typing import Optional


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tradable asset master table."""

    __tablename__ = "assets"

    symbol: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    asset_class: Mapped[AssetClass] = mapped_column(Enum(AssetClass, name="asset_class_enum"), nullable=False)
    base_currency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    quote_currency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    exchange: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    ibkr_con_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
