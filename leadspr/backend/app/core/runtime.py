from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.integrations.email.client import EmailClient
from app.integrations.google_sheets.client import SheetClient
from app.integrations.stripe.client import CheckoutClient
from app.services.email_service import EmailService
from app.services.fulfillment_service import FulfillmentService
from app.services.lead_sync_service import LeadSyncService
from app.services.purchase_service import PurchaseService
from app.services.webhook_service import WebhookService


@dataclass
class Runtime:
    config: Settings
    sessions: sessionmaker[Session]
    sheets: SheetClient
    stripe: CheckoutClient
    email_client: EmailClient

    def purchases(self) -> PurchaseService:
        return PurchaseService(self.sessions, self.config, self.stripe)

    def sync(self) -> LeadSyncService:
        return LeadSyncService(self.sessions, self.config, self.sheets)

    def email(self) -> EmailService:
        return EmailService(self.sessions, self.config, self.email_client)

    def webhooks(self) -> WebhookService:
        return WebhookService(
            self.stripe, FulfillmentService(self.sessions, self.config), self.email()
        )
