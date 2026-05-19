from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import JSONBType, CreatedAtMixin, UUIDPrimaryKeyMixin
from typing import Optional


class EvalCase(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Evaluation benchmark case."""

    __tablename__ = "eval_cases"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    input_json: Mapped[dict] = mapped_column(JSONBType, nullable=False)
    expected_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    scoring_rules_json: Mapped[Optional[dict]] = mapped_column(JSONBType, nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
