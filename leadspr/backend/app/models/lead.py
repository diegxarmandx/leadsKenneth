from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Text, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.models.purchase_lead import PurchaseLead


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(Text, unique=True, index=True)
    lead_date: Mapped[date] = mapped_column(Date, index=True)
    first_name: Mapped[str] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    municipality: Mapped[str | None] = mapped_column(Text, index=True)
    insurance_type: Mapped[str] = mapped_column(
        Text,
        default="Life Insurance",
        server_default="Life Insurance",
        index=True,
    )
    source: Mapped[str | None] = mapped_column(Text)
    campaign: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    source_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)
    last_synced_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    purchase_leads: Mapped[list["PurchaseLead"]] = relationship(back_populates="lead")
