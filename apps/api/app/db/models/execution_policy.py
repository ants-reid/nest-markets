from sqlalchemy import Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import AssetClass, ExecutionModeName
from app.db.models.mixins import JSONBType, CreatedAtMixin, UUIDPrimaryKeyMixin
from typing import Optional


class ExecutionPolicy(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Execution policy per asset class and mode."""

    __tablename__ = "execution_policies"

    asset_class: Mapped[AssetClass] = mapped_column(Enum(AssetClass, name="execution_policy_asset_class_enum"), nullable=False)
    mode: Mapped[ExecutionModeName] = mapped_column(Enum(ExecutionModeName, name="execution_policy_mode_enum"), nullable=False)
    allow_long: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    allow_short: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    allowed_timeframes_json: Mapped[Optional[list]] = mapped_column(JSONBType, nullable=True)
    requires_user_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    paper_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
