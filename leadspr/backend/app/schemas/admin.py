from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.integrations.google_sheets.parser import NormalizedLead
from app.models.enums import SyncStatus
from app.schemas.purchase import PurchaseResponse


class AdminLeadResponse(NormalizedLead):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_active: bool
    created_at: datetime
    updated_at: datetime
    last_synced_at: datetime | None
    age_days: int
    current_price_cents: int | None
    currently_excluded: bool
    excluded_until: datetime | None


class AdminPurchaseResponse(PurchaseResponse):
    buyer_name: str
    buyer_email: str
    buyer_phone: str | None
    stripe_checkout_id: str | None
    stripe_payment_intent: str | None


class SyncRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    started_at: datetime
    completed_at: datetime | None
    status: SyncStatus
    rows_received: int
    leads_created: int
    leads_updated: int
    leads_deactivated: int
    leads_reactivated: int
    error_message: str | None
