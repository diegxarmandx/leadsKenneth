from __future__ import annotations

from datetime import date

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError, NotFoundError, PricingRuleConflictError
from app.models import PricingRule
from app.models.enums import ActorType
from app.repositories.pricing_rule_repository import PricingRuleRepository
from app.schemas.pricing import PricingRuleInput, PricingRulePatch, PricingRuleUpdate
from app.services.audit_service import AuditService


class PricingService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = PricingRuleRepository(session)

    @staticmethod
    def age_days(lead_date: date, today: date) -> int:
        return (today - lead_date).days

    @staticmethod
    def applicable_rule(
        lead_date: date,
        today: date,
        rules: list[PricingRule],
    ) -> PricingRule | None:
        age = PricingService.age_days(lead_date, today)
        return next(
            (
                rule
                for rule in rules
                if rule.is_active
                and rule.min_age_days <= age
                and (rule.max_age_days is None or age <= rule.max_age_days)
            ),
            None,
        )

    @staticmethod
    def validate_ranges(rules: list[PricingRule | PricingRuleInput]) -> None:
        for rule in rules:
            PricingRuleInput.model_validate(rule, from_attributes=True)
        active = sorted((rule for rule in rules if rule.is_active), key=lambda r: r.min_age_days)
        if not active or active[0].min_age_days != 0:
            raise PricingRuleConflictError("Active pricing must cover every age starting at day 0")
        for left, right in zip(active, active[1:], strict=False):
            if left.max_age_days is None or right.min_age_days != left.max_age_days + 1:
                raise PricingRuleConflictError(
                    "Active ranges must be contiguous and cannot overlap"
                )
        if active[-1].max_age_days is not None:
            raise PricingRuleConflictError("The final active range must be open-ended")

    def list(self, active_only: bool = False) -> list[PricingRule]:
        return self.repository.list(active_only)

    def create(self, data: PricingRuleInput) -> PricingRule:
        self.validate_ranges([*self.list(), data])
        rule = self.repository.add(data.model_dump())
        self.session.flush()
        self._audit(rule, None)
        return rule

    def update(self, rule_id: int, data: PricingRulePatch) -> PricingRule:
        rule = self.repository.get(rule_id)
        if rule is None:
            raise NotFoundError("Pricing rule not found")
        # Checkout selects an exact price bucket. Keep edited tiers distinct so
        # changing a price cannot silently combine different age groups.
        if data.price_cents is not None and data.price_cents != rule.price_cents:
            if any(
                other.id != rule.id and other.is_active and other.price_cents == data.price_cents
                for other in self.list()
            ):
                raise PricingRuleConflictError("Another active age tier already uses this price")
        old = self._snapshot(rule)
        try:
            merged = PricingRuleInput(**(old | data.model_dump(exclude_unset=True)))
        except ValidationError as exc:
            raise DomainError("Invalid pricing range") from exc
        for key, value in merged.model_dump().items():
            setattr(rule, key, value)
        self.validate_ranges(self.list())
        self._audit(rule, old)
        self.session.flush()
        return rule

    def update_batch(self, data: list[PricingRuleUpdate]) -> list[PricingRule]:
        """Edit adjacent ranges atomically; preserve IDs referenced by purchase history."""
        existing = {rule.id: rule for rule in self.list()}
        ids = [item.id for item in data if item.id is not None]
        if len(ids) != len(set(ids)) or set(ids) != set(existing):
            raise DomainError("Include every existing rule exactly once; use id=null for new rules")
        self.validate_ranges(data)
        for item in data:
            values = item.model_dump(exclude={"id"})
            rule = existing.get(item.id)
            old = self._snapshot(rule) if rule else None
            if rule is None:
                rule = self.repository.add(values)
            else:
                for key, value in values.items():
                    setattr(rule, key, value)
            self.session.flush()
            self._audit(rule, old)
        return self.list()

    @staticmethod
    def _snapshot(rule: PricingRule) -> dict:
        return PricingRuleInput.model_validate(rule, from_attributes=True).model_dump()

    def _audit(self, rule: PricingRule, old: dict | None) -> None:
        AuditService(self.session).record(
            "pricing_rule.updated" if old else "pricing_rule.created",
            "pricing_rule",
            rule.id,
            actor=ActorType.ADMIN,
            old=old,
            new=self._snapshot(rule),
        )
