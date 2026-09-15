import logging
from datetime import timedelta

from filelock import FileLock, Timeout
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.exceptions import DomainError, EmailDeliveryBlocked, EmailDeliveryError, NotFoundError
from app.db.session import lock_path, write_session
from app.integrations.stripe.client import CheckoutClient
from app.models import AuditLog, Purchase
from app.models.enums import PurchaseStatus
from app.repositories.purchase_repository import PurchaseRepository
from app.schemas.purchase import PurchaseResponse
from app.services.audit_service import AuditService
from app.services.email_service import EmailService
from app.services.fulfillment_service import FulfillmentService
from app.utils.time import utcnow

logger = logging.getLogger(__name__)
ATTEMPT = "checkout.reconciliation_attempted"
RETRY_SECONDS = 15


class CheckoutReconciliationService:
    """Recover missed webhooks using only the server-stored Stripe session.

    Allocation and email use the same idempotent services as signed webhooks.
    A per-order process lock and persisted cooldown bound concurrent refreshes.
    """

    def __init__(
        self,
        factory: sessionmaker[Session],
        config: Settings,
        stripe: CheckoutClient,
        email: EmailService,
    ) -> None:
        self.factory, self.config, self.stripe, self.email = factory, config, stripe, email

    def _public(self, public_id: str) -> PurchaseResponse:
        with self.factory() as session:
            purchase = PurchaseRepository(session).by_public_id(public_id)
            if purchase is None:
                raise NotFoundError("Order not found")
            return PurchaseResponse.model_validate(purchase)

    def refresh(self, public_id: str) -> PurchaseResponse:
        # Validate existence before creating any lock file from a caller's input.
        self._public(public_id)
        with self.factory() as session:
            path = lock_path(session.get_bind(), f"checkout-{public_id}")
        try:
            with FileLock(path, timeout=0):
                return self._refresh(public_id)
        except Timeout:
            return self._public(public_id)

    def _refresh(self, public_id: str) -> PurchaseResponse:
        with write_session(self.factory) as session:
            purchase = PurchaseRepository(session).by_public_id(public_id)
            if purchase.status in {PurchaseStatus.FAILED, PurchaseStatus.FULFILLMENT_FAILED} or (
                purchase.status == PurchaseStatus.FULFILLED and purchase.email_sent_at
            ):
                return PurchaseResponse.model_validate(purchase)
            if session.scalar(select(self.email.blocked_query(public_id))):
                raise EmailDeliveryBlocked()
            last = session.scalar(
                select(func.max(AuditLog.created_at)).where(
                    AuditLog.action == ATTEMPT,
                    AuditLog.entity_id == public_id,
                )
            )
            if last and utcnow() - last < timedelta(seconds=RETRY_SECONDS):
                return PurchaseResponse.model_validate(purchase)
            checkout_id, status = purchase.stripe_checkout_id, purchase.status
            AuditService(session).record(ATTEMPT, "purchase", public_id)
        # Never hold the database write lock while retrieving a Stripe session.
        if status != PurchaseStatus.FULFILLED and checkout_id:
            checkout = self.stripe.retrieve_checkout(checkout_id)
            if (
                checkout.get("id") != checkout_id
                or checkout.get("client_reference_id") != public_id
                or checkout.get("metadata", {}).get("purchase_public_id") != public_id
            ):
                raise DomainError("Stripe Checkout reference does not match the stored order")
            fulfillment = FulfillmentService(self.factory, self.config)
            if checkout.get("status") == "complete" and checkout.get("payment_status") == "paid":
                fulfillment.payment_succeeded(checkout)
            elif checkout.get("status") == "expired":
                fulfillment.payment_failed(checkout)
        try:
            self.email.deliver(public_id)
        except EmailDeliveryBlocked:
            raise
        except Exception as exc:
            # Successful payment/allocation is already committed. Report delivery
            # failure honestly; the background job will retry the same email key.
            raise EmailDeliveryError(
                "Tus leads están asignados, pero no se pudo enviar el correo. "
                "Reintentaremos el envío automáticamente."
            ) from exc
        return self._public(public_id)

    def recover_pending(self) -> None:
        # Bounded recovery sweep; oldest checked orders yield to others on each run.
        # Older orders remain recoverable through the explicit refresh endpoint.
        last_attempt = (
            select(func.max(AuditLog.created_at))
            .where(
                AuditLog.action == ATTEMPT,
                AuditLog.entity_id == Purchase.public_id,
            )
            .correlate(Purchase)
            .scalar_subquery()
        )
        with self.factory() as session:
            ids = list(
                session.scalars(
                    select(Purchase.public_id)
                    .where(
                        Purchase.created_at >= utcnow() - timedelta(days=7),
                        ~self.email.blocked_query(Purchase.public_id),
                        or_(
                            Purchase.status.in_([PurchaseStatus.PENDING, PurchaseStatus.PAID]),
                            (Purchase.status == PurchaseStatus.FULFILLED)
                            & Purchase.email_sent_at.is_(None),
                        ),
                    )
                    .order_by(last_attempt.asc().nulls_first(), Purchase.created_at)
                    .limit(10)
                )
            )
        for public_id in ids:
            try:
                self.refresh(public_id)
            except EmailDeliveryBlocked:
                # First rejection is persisted and logged by EmailService.
                # Later sweeps exclude this order until an explicit admin retry.
                pass
            except Exception as exc:
                logger.error("Order recovery failed for %s: %s", public_id, type(exc).__name__)
