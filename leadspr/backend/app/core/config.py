from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("Use a valid IANA timezone") from exc
    return value


def validate_sync_time(value: str) -> str:
    from datetime import time

    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Use HH:MM in 24-hour time") from exc
    if len(value) != 5 or parsed.second or parsed.tzinfo:
        raise ValueError("Use HH:MM in 24-hour time")
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./leadspr.db"
    frontend_url: str = "http://localhost:3000"
    admin_api_token: SecretStr = SecretStr("")
    google_sheets_credentials_json: SecretStr = SecretStr("")
    google_sheet_id: str = ""
    google_sheet_tab: str = "Leads"
    stripe_secret_key: SecretStr = SecretStr("")
    stripe_webhook_secret: SecretStr = SecretStr("")
    stripe_success_url: str = "http://localhost:3000/checkout/success?order_id={PUBLIC_ID}"
    stripe_cancel_url: str = "http://localhost:3000/checkout/cancel"
    resend_api_key: SecretStr = SecretStr("")
    email_from: str = ""
    app_timezone: str = "America/Puerto_Rico"
    daily_sync_time: str = "02:00"
    scheduler_enabled: bool = True

    _timezone = field_validator("app_timezone")(validate_timezone)
    _sync_time = field_validator("daily_sync_time")(validate_sync_time)

    @field_validator("frontend_url", "stripe_success_url", "stripe_cancel_url")
    @classmethod
    def http_url(cls, value: str) -> str:
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Expected an absolute HTTP(S) URL")
        return value.rstrip("/")
