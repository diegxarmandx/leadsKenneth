from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PricingRule


class PricingRuleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, active_only: bool = False) -> list[PricingRule]:
        query = select(PricingRule).order_by(PricingRule.sort_order, PricingRule.id)
        if active_only:
            query = query.where(PricingRule.is_active.is_(True))
        return list(self.session.scalars(query))

    def get(self, rule_id: int) -> PricingRule | None:
        return self.session.get(PricingRule, rule_id)

    def add(self, values: dict) -> PricingRule:
        rule = PricingRule(**values)
        self.session.add(rule)
        return rule
