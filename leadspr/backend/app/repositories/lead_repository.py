from datetime import date, datetime

from sqlalchemy import Select, and_, false, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models import Lead, PricingRule, PurchaseLead


class LeadRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def age_condition(rule: PricingRule, today: date) -> ColumnElement[bool]:
        upper = today.toordinal() - rule.min_age_days
        if upper < 1:
            return false()
        condition = Lead.lead_date <= date.fromordinal(upper)
        if rule.max_age_days is not None:
            lower = max(1, today.toordinal() - rule.max_age_days)
            condition = and_(condition, Lead.lead_date >= date.fromordinal(lower))
        return condition

    def eligible_query(
        self,
        rules: list[PricingRule],
        today: date,
        now: datetime,
        insurance_type: str = "Life Insurance",
        municipality: str | None = None,
    ) -> Select[tuple[Lead]]:
        excluded = (
            select(PurchaseLead.id)
            .where(
                PurchaseLead.lead_id == Lead.id,
                PurchaseLead.excluded_until > now,
            )
            .exists()
        )
        ranges = [self.age_condition(rule, today) for rule in rules if rule.is_active]
        query = select(Lead).where(
            Lead.source_active.is_(True),
            Lead.insurance_type == insurance_type,
            Lead.lead_date <= today,
            ~excluded,
            or_(*ranges) if ranges else false(),
        )
        if municipality:
            query = query.where(Lead.municipality == municipality)
        return query

    def count(self, query: Select[tuple[Lead]]) -> int:
        return self.session.scalar(select(func.count()).select_from(query.subquery())) or 0

    def random_selection(self, query: Select[tuple[Lead]], quantity: int) -> list[Lead]:
        # Kept here so a future database-specific strategy does not change business logic.
        return list(self.session.scalars(query.order_by(func.random()).limit(quantity)))

    def by_external_id(self) -> dict[str, Lead]:
        return {lead.external_id: lead for lead in self.session.scalars(select(Lead))}

    def add(self, **values) -> Lead:
        lead = Lead(**values)
        self.session.add(lead)
        return lead
