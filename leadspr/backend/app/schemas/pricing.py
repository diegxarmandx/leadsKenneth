from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PricingRuleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_age_days: int = Field(ge=0, strict=True)
    max_age_days: int | None = Field(default=None, ge=0, strict=True)
    price_cents: int = Field(gt=0, strict=True)
    exclusion_days: int = Field(ge=0, strict=True)
    sort_order: int = Field(default=0, strict=True)
    is_active: bool = True

    @model_validator(mode="after")
    def valid_range(self) -> Self:
        if self.max_age_days is not None and self.max_age_days < self.min_age_days:
            raise ValueError("max_age_days must be >= min_age_days")
        return self


class PricingRulePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_age_days: int | None = Field(default=None, ge=0, strict=True)
    max_age_days: int | None = Field(default=None, ge=0, strict=True)
    price_cents: int | None = Field(default=None, gt=0, strict=True)
    exclusion_days: int | None = Field(default=None, ge=0, strict=True)
    sort_order: int | None = Field(default=None, strict=True)
    is_active: bool | None = None

    @model_validator(mode="after")
    def no_null_required_fields(self) -> Self:
        for field in self.model_fields_set - {"max_age_days"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class PricingRuleUpdate(PricingRuleInput):
    id: int | None = Field(default=None, gt=0)


class PricingRuleResponse(PricingRuleInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
