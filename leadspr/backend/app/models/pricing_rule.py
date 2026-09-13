from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.models.purchase_lead import PurchaseLead


class PricingRule(Base):
    __tablename__ = "pricing_rules"
    __table_args__ = (
        CheckConstraint("min_age_days >= 0", name="nonnegative_min_age"),
        CheckConstraint("max_age_days IS NULL OR max_age_days >= min_age_days", name="valid_range"),
        CheckConstraint("price_cents > 0", name="positive_price"),
        CheckConstraint("exclusion_days >= 0", name="nonnegative_exclusion"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    min_age_days: Mapped[int]
    max_age_days: Mapped[int | None]
    price_cents: Mapped[int]
    exclusion_days: Mapped[int]
    sort_order: Mapped[int]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)

    purchase_leads: Mapped[list["PurchaseLead"]] = relationship(back_populates="pricing_rule")
