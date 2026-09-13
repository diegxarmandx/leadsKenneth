from datetime import date, datetime

from sqlalchemy import Row, false, func, or_, select
from sqlalchemy.orm import Session

from app.models import Lead, PricingRule, Purchase, PurchaseLead
from app.models.enums import PurchaseStatus
from app.repositories.lead_repository import LeadRepository


class AdminRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def leads(
        self,
        *,
        rules: list[PricingRule],
        today: date,
        offset: int,
        limit: int,
        external_id: str | None,
        municipality: str | None,
        source_active: bool | None,
        price_cents: int | None,
        min_age_days: int | None,
        max_age_days: int | None,
    ) -> tuple[int, list[Row[tuple[Lead, datetime | None]]]]:
        last_exclusion = (
            select(func.max(PurchaseLead.excluded_until))
            .where(
                PurchaseLead.lead_id == Lead.id,
            )
            .correlate(Lead)
            .scalar_subquery()
        )
        query = select(Lead, last_exclusion.label("excluded_until"))
        if external_id:
            query = query.where(Lead.external_id == external_id)
        if municipality:
            query = query.where(Lead.municipality == municipality)
        if source_active is not None:
            query = query.where(Lead.source_active == source_active)
        if price_cents is not None:
            ranges = [
                LeadRepository.age_condition(rule, today)
                for rule in rules
                if rule.is_active and rule.price_cents == price_cents
            ]
            query = query.where(or_(*ranges) if ranges else false())
        if min_age_days is not None:
            ordinal = today.toordinal() - min_age_days
            query = query.where(
                Lead.lead_date <= date.fromordinal(ordinal) if ordinal > 0 else false()
            )
        if max_age_days is not None:
            query = query.where(
                Lead.lead_date >= date.fromordinal(max(1, today.toordinal() - max_age_days))
            )
        total = self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self.session.execute(query.order_by(Lead.id).offset(offset).limit(limit)).all()
        return total, rows

    def purchases(
        self,
        *,
        offset: int,
        limit: int,
        status: PurchaseStatus | None,
        buyer_email: str | None,
        public_id: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> tuple[int, list[Purchase]]:
        query = select(Purchase)
        for column, value in (
            (Purchase.status, status),
            (Purchase.buyer_email, buyer_email),
            (Purchase.public_id, public_id),
        ):
            if value is not None:
                query = query.where(column == value)
        if created_from:
            query = query.where(Purchase.created_at >= created_from)
        if created_to:
            query = query.where(Purchase.created_at < created_to)
        total = self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self.session.scalars(query.order_by(Purchase.id.desc()).offset(offset).limit(limit))
        return total, list(rows)
