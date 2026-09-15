import json
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import InstrumentedAttribute, Session, sessionmaker
from sqlalchemy.sql import ColumnElement

from app.core.config import Settings
from app.core.exceptions import EmailDeliveryBlocked, FulfillmentError, NotFoundError
from app.db.session import write_session
from app.integrations.email.client import EmailClient
from app.integrations.email.template import delivery_payload
from app.models import AuditLog
from app.models.enums import ActorType, PurchaseStatus
from app.repositories.audit_repository import AuditRepository
from app.repositories.purchase_repository import PurchaseRepository
from app.services.audit_service import AuditService
from app.services.settings_service import SettingsService
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def blocked_query(public_id: str | InstrumentedAttribute[str]) -> ColumnElement[bool]:
        # Blocks survive restarts and transient admin retry failures. Only a
        # confirmed successful delivery supersedes a permanent rejection.
        latest = (
            select(AuditLog.action)
            .where(
                AuditLog.entity_id == public_id,
                AuditLog.action.in_(["email.blocked", "email.sent", "email.resent"]),
            )
            .order_by(AuditLog.id.desc())
            .limit(1)
            .correlate_except(AuditLog)
            .scalar_subquery()
        )
        return func.coalesce(latest, "") == "email.blocked"

    def __init__(
        self, factory: sessionmaker[Session], config: Settings, client: EmailClient
    ) -> None:
        self.factory, self.config, self.client = factory, config, client

    def deliver(self, public_id: str, resend_key: str | None = None) -> bool:
        failure: Exception | None = None
        # Serialize concurrent delivery attempts as well. This deliberately holds the MVP
        # SQLite lock over a bounded network call; allocation has already committed.
        with write_session(self.factory) as session:
            purchase = PurchaseRepository(session).by_public_id(public_id, with_leads=True)
            if purchase is None:
                raise NotFoundError("Order not found")
            if purchase.status != PurchaseStatus.FULFILLED:
                if resend_key:
                    raise FulfillmentError("Only fulfilled orders can be emailed")
                return False
            if purchase.email_sent_at and not resend_key:
                return True
            if not resend_key and session.scalar(select(self.blocked_query(public_id))):
                raise EmailDeliveryBlocked()
            resend_values = {"idempotency_key": resend_key} if resend_key else None
            if resend_key and AuditRepository(session).has_action(
                "email.resent",
                public_id,
                json.dumps(resend_values),
            ):
                return True
            settings = SettingsService(session, self.config).all()
            payload = delivery_payload(purchase, settings["sender_email"], settings["company_name"])
            key = f"resend/{public_id}/{resend_key}" if resend_key else f"delivery/{public_id}"
            audit = AuditService(session)
            try:
                message_id = self.client.send(payload, key)
            except EmailDeliveryBlocked as exc:
                failure = exc
                audit.record(
                    "email.blocked",
                    "purchase",
                    public_id,
                    new={
                        "error_type": type(exc).__name__,
                        "provider_status": exc.provider_status,
                        "reason": exc.reason,
                        "retryable": False,
                    },
                )
                logger.warning(
                    "Email delivery paused; correct the recipient or sender configuration "
                    "before an admin retry",
                    extra={
                        "public_id": public_id,
                        "provider_status": exc.provider_status,
                        "provider_reason": exc.reason,
                    },
                )
            except Exception as exc:
                failure = exc
                audit.record(
                    "email.failed", "purchase", public_id, new={"error_type": type(exc).__name__}
                )
                logger.error(
                    "Fulfillment email failed",
                    extra={"public_id": public_id, "error_type": type(exc).__name__},
                )
            else:
                purchase.email_sent_at = utcnow()
                audit.record(
                    "email.accepted", "purchase", public_id, new={"provider_message_id": message_id}
                )
                audit.record(
                    "email.resent" if resend_key else "email.sent",
                    "purchase",
                    public_id,
                    actor=ActorType.ADMIN if resend_key else ActorType.SYSTEM,
                    new=resend_values,
                )
        # Persist failure evidence without rolling back successful allocation.
        if failure:
            raise failure
        return True
