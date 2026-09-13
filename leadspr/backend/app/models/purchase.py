from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime
from app.models.enums import PurchaseStatus
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.models.purchase_lead import PurchaseLead


class Purchase(Base):
    __tablename__ = "purchases"
    __table_args__ = (
        CheckConstraint("requested_quantity > 0", name="positive_quantity"),
        CheckConstraint("price_per_lead_cents > 0", name="positive_price"),
        CheckConstraint(
            "total_amount_cents = requested_quantity * price_per_lead_cents",
            name="correct_total",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(Text, unique=True)
    buyer_name: Mapped[str] = mapped_column(Text)
    buyer_email: Mapped[str] = mapped_column(Text)
    buyer_phone: Mapped[str | None] = mapped_column(Text)
    insurance_type: Mapped[str] = mapped_column(
        Text,
        default="Life Insurance",
        server_default="Life Insurance",
    )
    municipality: Mapped[str | None] = mapped_column(Text)
    requested_quantity: Mapped[int]
    price_per_lead_cents: Mapped[int]
    total_amount_cents: Mapped[int]
    stripe_checkout_id: Mapped[str | None] = mapped_column(Text, unique=True)
    stripe_payment_intent: Mapped[str | None] = mapped_column(Text, unique=True, index=True)
    status: Mapped[PurchaseStatus] = mapped_column(
        Enum(PurchaseStatus, native_enum=False, create_constraint=True, name="purchase_status"),
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    fulfilled_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    email_sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    purchase_leads: Mapped[list["PurchaseLead"]] = relationship(back_populates="purchase")
