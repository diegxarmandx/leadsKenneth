from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime

if TYPE_CHECKING:
    from app.models.lead import Lead
    from app.models.pricing_rule import PricingRule
    from app.models.purchase import Purchase


class PurchaseLead(Base):
    __tablename__ = "purchase_leads"
    __table_args__ = (
        UniqueConstraint("purchase_id", "lead_id"),
        CheckConstraint("price_paid_cents > 0", name="positive_price"),
        CheckConstraint("excluded_until >= purchased_at", name="valid_exclusion"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id", ondelete="RESTRICT"))
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="RESTRICT"),
        index=True,
    )
    pricing_rule_id: Mapped[int] = mapped_column(
        ForeignKey("pricing_rules.id", ondelete="RESTRICT")
    )
    price_paid_cents: Mapped[int]
    purchased_at: Mapped[datetime] = mapped_column(UTCDateTime())
    excluded_until: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)

    purchase: Mapped["Purchase"] = relationship(back_populates="purchase_leads")
    lead: Mapped["Lead"] = relationship(back_populates="purchase_leads")
    pricing_rule: Mapped["PricingRule"] = relationship(back_populates="purchase_leads")
