import json
import logging
from dataclasses import dataclass
from typing import Protocol

import stripe

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, DomainError, IntegrationError
from app.models import Purchase

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CheckoutSession:
    id: str
    url: str


class CheckoutClient(Protocol):
    def create_checkout(self, purchase: Purchase) -> CheckoutSession: ...
    def verify_event(self, payload: bytes, signature: str) -> dict: ...


class StripeClient:
    def __init__(self, config: Settings) -> None:
        self.config = config

    def create_checkout(self, purchase: Purchase) -> CheckoutSession:
        key = self.config.stripe_secret_key.get_secret_value()
        if not key:
            raise ConfigurationError("Configure STRIPE_SECRET_KEY before creating Checkout")
        try:
            client = stripe.StripeClient(
                key,
                max_network_retries=2,
                http_client=stripe.RequestsClient(timeout=20),
            )
            session = client.v1.checkout.sessions.create(
                params={
                    "mode": "payment",
                    "locale": "es-419",
                    "managed_payments": {
                        "enabled": False,
                    },
                    "customer_email": purchase.buyer_email,
                    "client_reference_id": purchase.public_id,
                    "metadata": {"purchase_public_id": purchase.public_id},
                    "payment_intent_data": {
                        "metadata": {"purchase_public_id": purchase.public_id},
                    },
                    "line_items": [
                        {
                            "quantity": purchase.requested_quantity,
                            "price_data": {
                                "currency": "usd",
                                "unit_amount": purchase.price_per_lead_cents,
                                "product_data": {
                                    "name": "Borinquen Life & Protection · Leads de seguro de vida"
                                },
                            },
                        }
                    ],
                    "success_url": self.config.stripe_success_url.replace(
                        "{PUBLIC_ID}",
                        purchase.public_id,
                    ),
                    "cancel_url": self.config.stripe_cancel_url,
                },
                options={"idempotency_key": f"checkout/{purchase.public_id}"},
            )
            if not session.url:
                raise IntegrationError("Stripe did not return a Checkout URL")
            return CheckoutSession(id=session.id, url=session.url)
        except IntegrationError:
            raise
        except Exception as exc:
            logger.exception("Stripe Checkout API error: %s", exc)
            raise IntegrationError("Unable to create Stripe Checkout; try again later") from exc

    def verify_event(self, payload: bytes, signature: str) -> dict:
        secret = self.config.stripe_webhook_secret.get_secret_value()
        if not secret:
            raise ConfigurationError("Configure STRIPE_WEBHOOK_SECRET before receiving webhooks")
        try:
            stripe.Webhook.construct_event(payload, signature, secret, tolerance=300)
            return json.loads(payload)
        except (ValueError, stripe.SignatureVerificationError) as exc:
            raise DomainError("Invalid Stripe webhook signature or payload") from exc
