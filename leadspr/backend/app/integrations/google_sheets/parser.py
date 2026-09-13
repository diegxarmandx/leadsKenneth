from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, TypeAdapter, ValidationError

from app.core.exceptions import SheetSyncError

REQUIRED = {"external_id", "lead_date", "first_name", "phone"}
OPTIONAL = {
    "last_name",
    "email",
    "municipality",
    "insurance_type",
    "source",
    "campaign",
    "language",
    "notes",
}


class NormalizedLead(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    external_id: str = Field(min_length=1)
    lead_date: date
    first_name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    last_name: str | None = None
    email: str | None = None
    municipality: str | None = None
    insurance_type: str = "Life Insurance"
    source: str | None = None
    campaign: str | None = None
    language: str | None = None
    notes: str | None = None


@dataclass
class ParseResult:
    leads: list[NormalizedLead] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)


def clean_cell(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ValueError("Expected a scalar cell")
    return str(value).strip() or None


def values_to_rows(values: list[list[Any]]) -> list[dict[str, Any]]:
    if not values:
        raise SheetSyncError("Sheet must contain a header row; no local leads were changed")
    headers = [str(value).strip().lower() for value in values[0]]
    populated = [header for header in headers if header]
    if len(set(populated)) != len(populated) or not REQUIRED.issubset(headers):
        raise SheetSyncError(
            "Sheet headers must be unique and contain external_id, lead_date, first_name, and phone"
        )
    rows = []
    for row in values[1:]:
        # Preserve empty physical rows so validation messages use real sheet row numbers.
        if len(row) > len(headers) and any(str(cell).strip() for cell in row[len(headers) :]):
            raise SheetSyncError("A row contains data beyond the header columns")
        rows.append(
            {header: row[i] if i < len(row) else None for i, header in enumerate(headers) if header}
        )
    return rows


def parse_rows(rows: list[dict[str, Any]]) -> ParseResult:
    result = ParseResult()
    seen: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        if not any(value is not None and str(value).strip() for value in row.values()):
            continue
        cleaned: dict[str, Any] = {}
        invalid: set[str] = set()
        for name in REQUIRED | OPTIONAL:
            try:
                cleaned[name] = clean_cell(row.get(name))
            except ValueError:
                cleaned[name] = None
                if name in REQUIRED:
                    invalid.add(name)
                else:
                    result.warnings.append(
                        {"row": row_number, "field": name, "error": "invalid_optional_value"}
                    )
        external_id = cleaned["external_id"]
        if external_id:
            if external_id in seen:
                raise SheetSyncError(f"Duplicate external_id at row {row_number}; sync aborted")
            seen.add(external_id)
        cleaned["insurance_type"] = cleaned["insurance_type"] or "Life Insurance"
        if cleaned["email"]:
            try:
                cleaned["email"] = str(TypeAdapter(EmailStr).validate_python(cleaned["email"]))
            except ValidationError:
                cleaned["email"] = None
                result.warnings.append(
                    {"row": row_number, "field": "email", "error": "invalid_optional_value"}
                )
        try:
            # ISO calendar dates are explicit; ambiguous locale-specific dates are rejected.
            cleaned["lead_date"] = date.fromisoformat(cleaned["lead_date"] or "")
        except ValueError:
            invalid.add("lead_date")
        try:
            lead = NormalizedLead(**cleaned)
        except ValidationError as exc:
            invalid.update(str(error["loc"][0]) for error in exc.errors())
        if invalid:
            result.rejected.append(
                {"row": row_number, "fields": sorted(invalid), "error": "invalid_required_fields"}
            )
        else:
            result.leads.append(lead)
    return result
