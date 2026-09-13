from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import PurchaseStatus

InsuranceType = Literal["Life Insurance"]


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    buyer_name: str = Field(min_length=1, max_length=200)
    buyer_email: EmailStr
    buyer_phone: str | None = Field(default=None, max_length=50)
    insurance_type: InsuranceType = "Life Insurance"
    municipality: str | None = Field(default=None, max_length=100)
    price_per_lead_cents: int = Field(gt=0, strict=True)
    quantity: int = Field(gt=0, strict=True)

    @field_validator("municipality", "buyer_phone")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        return value or None


class CheckoutResponse(BaseModel):
    public_id: str
    checkout_session_id: str
    checkout_url: str


class PurchaseResponse(BaseModel):
    """Explicit allowlist: never expose buyer PII, internal IDs, or payment identifiers."""

    model_config = ConfigDict(from_attributes=True)
    public_id: str
    status: PurchaseStatus
    insurance_type: str
    municipality: str | None
    requested_quantity: int
    price_per_lead_cents: int
    total_amount_cents: int
    created_at: datetime
    paid_at: datetime | None
    fulfilled_at: datetime | None
    email_sent_at: datetime | None
