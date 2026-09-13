import logging
import secrets

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.db.session import write_session
from app.integrations.stripe.client import CheckoutClient
from app.models.enums import PurchaseStatus
from app.repositories.purchase_repository import PurchaseRepository
from app.schemas.purchase import CheckoutRequest, CheckoutResponse, PurchaseResponse
from app.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)
PUBLIC_ID_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


class PurchaseService:
    def __init__(
        self, factory: sessionmaker[Session], config: Settings, stripe: CheckoutClient
    ) -> None:
        self.factory, self.config, self.stripe = factory, config, stripe

    def create_checkout(self, data: CheckoutRequest) -> CheckoutResponse:
        with write_session(self.factory) as session:
            inventory = InventoryService(session, self.config)
            inventory.validate_quantity(
                data.quantity,
                price_cents=data.price_per_lead_cents,
                municipality=data.municipality,
                insurance_type=data.insurance_type,
            )
            repository = PurchaseRepository(session)
            public_id = self._public_id()
            while repository.by_public_id(public_id):
                public_id = self._public_id()
            purchase = repository.add(
                public_id=public_id,
                buyer_name=data.buyer_name,
                buyer_email=str(data.buyer_email),
                buyer_phone=data.buyer_phone,
                municipality=data.municipality,
                insurance_type=data.insurance_type,
                requested_quantity=data.quantity,
                price_per_lead_cents=data.price_per_lead_cents,
                total_amount_cents=data.quantity * data.price_per_lead_cents,
                status=PurchaseStatus.PENDING,
            )
        # Commit the order before the network call. No lead has been assigned or reserved.
        try:
            checkout = self.stripe.create_checkout(purchase)
        except Exception as exc:
            with write_session(self.factory) as session:
                saved = PurchaseRepository(session).by_public_id(public_id)
                if saved is not None and saved.status == PurchaseStatus.PENDING:
                    saved.status = PurchaseStatus.FAILED
            logger.exception(
                "Checkout creation failed for %s: %s",
                public_id,
                exc,
            )
            raise
        with write_session(self.factory) as session:
            saved = PurchaseRepository(session).by_public_id(public_id)
            saved.stripe_checkout_id = checkout.id
        return CheckoutResponse(
            public_id=public_id, checkout_session_id=checkout.id, checkout_url=checkout.url
        )

    def get_public(self, public_id: str) -> PurchaseResponse:
        with self.factory() as session:
            purchase = PurchaseRepository(session).by_public_id(public_id)
            if purchase is None:
                raise NotFoundError("Order not found")
            return PurchaseResponse.model_validate(purchase)

    @staticmethod
    def _public_id() -> str:
        # 12 unambiguous random characters also make public status URLs hard to enumerate.
        return "ORD-" + "".join(secrets.choice(PUBLIC_ID_ALPHABET) for _ in range(12))
