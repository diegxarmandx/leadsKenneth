import logging
from app.core.exceptions import DomainError
from app.integrations.stripe.client import CheckoutClient
from app.services.email_service import EmailService
from app.services.fulfillment_service import FulfillmentService


logger = logging.getLogger(__name__)


class WebhookService:
    def __init__(
        self, stripe: CheckoutClient, fulfillment: FulfillmentService, email: EmailService
    ) -> None:
        self.stripe, self.fulfillment, self.email = stripe, fulfillment, email

    def process(self, payload: bytes, signature: str) -> dict:
        event = self.stripe.verify_event(payload, signature)
        kind = event.get("type")
        supported = {
            "checkout.session.completed",
            "checkout.session.async_payment_succeeded",
            "checkout.session.async_payment_failed",
            "checkout.session.expired",
        }
        if kind not in supported:
            return {"received": True}
        checkout = event.get("data", {}).get("object")
        if not isinstance(checkout, dict):
            raise DomainError("Invalid Checkout event")
        # Ignore other products using the same Stripe account.
        if not checkout.get("metadata", {}).get("purchase_public_id"):
            return {"received": True}
        if kind in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
            if checkout.get("payment_status") == "paid":
                public_id = self.fulfillment.payment_succeeded(checkout)
                try:
                    self.email.deliver(public_id)
                except Exception as exc:
                    logger.exception(
                        "Post-fulfillment email delivery failed for %s: %s",
                        public_id,
                        exc,
                    )
        else:
            self.fulfillment.payment_failed(checkout)
        return {"received": True}
