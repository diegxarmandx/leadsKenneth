from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.exceptions import (
    DomainError,
    InsufficientInventoryError,
    NotFoundError,
    PricingRuleNotFoundError,
)
from app.db.session import write_session
from app.models import Purchase
from app.models.enums import PurchaseStatus
from app.repositories.purchase_repository import PurchaseRepository
from app.services.audit_service import AuditService
from app.services.inventory_service import InventoryService
from app.services.pricing_service import PricingService
from app.utils.time import utcnow

TERMINAL = {PurchaseStatus.FULFILLED, PurchaseStatus.FULFILLMENT_FAILED}


class FulfillmentService:
    def __init__(self, factory: sessionmaker[Session], config: Settings) -> None:
        self.factory, self.config = factory, config

    def payment_succeeded(self, checkout: dict, now: datetime | None = None) -> str:
        if checkout.get("payment_status") != "paid":
            raise DomainError("Checkout has not been paid")
        with write_session(self.factory) as session:
            now = now or utcnow()
            purchase = self._find_and_bind(session, checkout)
            if purchase.status in TERMINAL:
                return purchase.public_id
            intent = checkout.get("payment_intent")
            if not isinstance(intent, str) or not intent.startswith("pi_"):
                raise DomainError("Paid Checkout is missing a payment intent")
            duplicate = session.scalar(
                select(Purchase.id).where(
                    Purchase.stripe_payment_intent == intent,
                    Purchase.id != purchase.id,
                )
            )
            if duplicate:
                raise DomainError("Payment intent is already associated with another order")
            if purchase.stripe_payment_intent and purchase.stripe_payment_intent != intent:
                raise DomainError("Payment intent does not match this order")
            purchase.stripe_payment_intent = intent
            purchase.paid_at = purchase.paid_at or now
            purchase.status = PurchaseStatus.PAID
            if (
                checkout.get("currency") != "usd"
                or checkout.get("amount_total") != purchase.total_amount_cents
                or checkout.get("mode") != "payment"
            ):
                self._fail(session, purchase, "payment_details_mismatch")
                return purchase.public_id
            inventory = InventoryService(session, self.config, now)
            try:
                leads = inventory.select_random(
                    purchase.requested_quantity,
                    price_cents=purchase.price_per_lead_cents,
                    municipality=purchase.municipality,
                    insurance_type=purchase.insurance_type,
                )
            except (InsufficientInventoryError, PricingRuleNotFoundError):
                self._fail(session, purchase, "post_payment_inventory_unavailable")
                return purchase.public_id
            repository = PurchaseRepository(session)
            for lead in leads:
                rule = PricingService.applicable_rule(
                    lead.lead_date, inventory.today, inventory.rules
                )
                if rule is None:
                    raise RuntimeError("Eligible lead has no active pricing rule")
                repository.add_allocation(
                    purchase_id=purchase.id,
                    lead_id=lead.id,
                    pricing_rule_id=rule.id,
                    price_paid_cents=purchase.price_per_lead_cents,
                    purchased_at=now,
                    excluded_until=now + timedelta(days=rule.exclusion_days),
                )
            purchase.status = PurchaseStatus.FULFILLED
            purchase.fulfilled_at = now
            # The transaction commits every allocation and order state together, or none.
            return purchase.public_id

    def payment_failed(self, checkout: dict) -> None:
        with write_session(self.factory) as session:
            purchase = self._find_and_bind(session, checkout)
            if purchase.status == PurchaseStatus.PENDING:
                purchase.status = PurchaseStatus.FAILED

    @staticmethod
    def _find_and_bind(session: Session, checkout: dict) -> Purchase:
        public_id = checkout.get("metadata", {}).get("purchase_public_id")
        if not isinstance(public_id, str):
            raise DomainError("Checkout is missing the order reference")
        purchase = PurchaseRepository(session).by_public_id(public_id)
        if purchase is None:
            raise NotFoundError("Order referenced by Checkout was not found")
        checkout_id = checkout.get("id")
        if not isinstance(checkout_id, str) or not checkout_id.startswith("cs_"):
            raise DomainError("Invalid Checkout session ID")
        if checkout.get("client_reference_id") != purchase.public_id:
            raise DomainError("Checkout reference does not match the order")
        if purchase.stripe_checkout_id and purchase.stripe_checkout_id != checkout_id:
            raise DomainError("Checkout session does not match the order")
        # A signed event can arrive before create_checkout saves the session ID.
        purchase.stripe_checkout_id = checkout_id
        return purchase

    @staticmethod
    def _fail(session: Session, purchase: Purchase, reason: str) -> None:
        purchase.status = PurchaseStatus.FULFILLMENT_FAILED
        AuditService(session).record(
            "fulfillment.failed",
            "purchase",
            purchase.public_id,
            new={"reason": reason, "requested_quantity": purchase.requested_quantity},
        )
