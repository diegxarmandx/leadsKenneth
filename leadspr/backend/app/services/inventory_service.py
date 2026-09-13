from datetime import datetime

from sqlalchemy import Select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import InsufficientInventoryError, PricingRuleNotFoundError
from app.models import Lead
from app.repositories.lead_repository import LeadRepository
from app.services.pricing_service import PricingService
from app.services.settings_service import SettingsService
from app.utils.time import business_date, utcnow


class InventoryService:
    def __init__(self, session: Session, config: Settings, now: datetime | None = None) -> None:
        self.session = session
        self.now = now or utcnow()
        self.today = business_date(SettingsService(session, config).all()["timezone"], self.now)
        self.rules = PricingService(session).list(active_only=True)
        self.repository = LeadRepository(session)

    def query(
        self,
        price_cents: int | None = None,
        municipality: str | None = None,
        insurance_type: str = "Life Insurance",
    ) -> Select[tuple[Lead]]:
        rules = (
            self.rules
            if price_cents is None
            else [rule for rule in self.rules if rule.price_cents == price_cents]
        )
        if price_cents is not None and not rules:
            raise PricingRuleNotFoundError("That exact price tier is not currently active")
        return self.repository.eligible_query(
            rules,
            self.today,
            self.now,
            insurance_type,
            municipality,
        )

    def count(self, **filters) -> int:
        return self.repository.count(self.query(**filters))

    def validate_quantity(self, quantity: int, **filters) -> None:
        count = self.count(**filters)
        if quantity <= 0 or quantity > count:
            raise InsufficientInventoryError(f"Requested quantity is unavailable; {count} eligible")

    def summary(
        self, municipality: str | None = None, insurance_type: str = "Life Insurance"
    ) -> dict:
        tiers: dict[int, dict] = {}
        for rule in self.rules:
            tier = tiers.setdefault(
                rule.price_cents,
                {
                    "price_cents": rule.price_cents,
                    "available_quantity": 0,
                    "age_ranges": [],
                },
            )
            query = self.repository.eligible_query(
                [rule],
                self.today,
                self.now,
                insurance_type,
                municipality,
            )
            tier["available_quantity"] += self.repository.count(query)
            tier["age_ranges"].append(
                {
                    "min_age_days": rule.min_age_days,
                    "max_age_days": rule.max_age_days,
                }
            )
        return {"as_of": self.now, "business_date": self.today, "tiers": list(tiers.values())}

    def municipalities(self, insurance_type: str = "Life Insurance") -> list[str]:
        query = self.query(insurance_type=insurance_type).with_only_columns(Lead.municipality)
        return list(
            self.session.scalars(
                query.where(
                    Lead.municipality.is_not(None),
                    Lead.municipality != "",
                )
                .distinct()
                .order_by(Lead.municipality)
            )
        )

    def select_random(self, quantity: int, **filters) -> list[Lead]:
        query = self.query(**filters)
        if self.repository.count(query) < quantity:
            raise InsufficientInventoryError("Inventory changed after Checkout")
        leads = self.repository.random_selection(query, quantity)
        if len(leads) != quantity:
            raise InsufficientInventoryError("Inventory changed during allocation")
        return leads
