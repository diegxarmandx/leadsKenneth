from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings, validate_sync_time, validate_timezone
from app.core.exceptions import DomainError
from app.models.enums import ActorType
from app.repositories.settings_repository import SettingsRepository
from app.services.audit_service import AuditService


class SettingsService:
    def __init__(self, session: Session, config: Settings) -> None:
        self.repository = SettingsRepository(session)
        self.audit = AuditService(session)
        self.defaults = {
            "google_sheet_id": config.google_sheet_id,
            "google_sheet_tab": config.google_sheet_tab,
            "daily_sync_time": config.daily_sync_time,
            "timezone": config.app_timezone,
            "company_name": "LeadsPR",
            "sender_email": config.email_from,
        }

    def all(self) -> dict[str, str]:
        stored = self.repository.all()
        return {key: stored.get(key, default) for key, default in self.defaults.items()}

    def update(self, values: dict[str, str]) -> dict[str, str]:
        if values.keys() - self.defaults.keys():
            raise DomainError("Only documented non-secret settings may be changed")
        for key, value in values.items():
            if not value.strip() or len(value) > 500:
                raise DomainError(f"{key} must contain 1–500 characters")
            try:
                if key == "timezone":
                    validate_timezone(value)
                elif key == "daily_sync_time":
                    validate_sync_time(value)
                elif key == "sender_email":
                    TypeAdapter(EmailStr).validate_python(value)
            except (ValueError, ValidationError) as exc:
                raise DomainError(f"Invalid value for {key}") from exc
        old = self.all()
        for key, value in values.items():
            self.repository.set(key, value)
            self.audit.record(
                "setting.updated",
                "app_setting",
                key,
                actor=ActorType.ADMIN,
                old={"value": old[key]},
                new={"value": value},
            )
        return old | values
