import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.data.municipalities import MUNICIPALITIES
from app.schemas.admin import SyncRunResponse


class LeadEntryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone: str = Field(min_length=7, max_length=30)
    email: EmailStr | None = None
    municipality: str
    lead_date: date

    @field_validator("last_name", "email", mode="before")
    @classmethod
    def blank_optional(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("phone")
    @classmethod
    def phone_format(cls, value: str) -> str:
        if (
            not re.fullmatch(r"\+?[0-9() .-]+", value)
            or not 7 <= len(re.sub(r"\D", "", value)) <= 15
        ):
            raise ValueError("Ingresa un teléfono válido de 7 a 15 dígitos.")
        return value

    @field_validator("municipality")
    @classmethod
    def municipality_exists(cls, value: str) -> str:
        if value not in MUNICIPALITIES:
            raise ValueError("Selecciona un municipio válido de Puerto Rico.")
        return value

    @field_validator("lead_date", mode="before")
    @classmethod
    def calendar_date(cls, value):
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("Usa una fecha válida en formato YYYY-MM-DD.")
        return value


class LeadEntryResponse(BaseModel):
    external_id: str
    sheet_written: Literal[True] = True
    appended: bool
    status: Literal["synced", "sync_pending"]
    available: bool = False
    sync_run: SyncRunResponse | None = None
