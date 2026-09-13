from typing import Protocol
import logging

import httpx

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, IntegrationError

logger = logging.getLogger(__name__)


class EmailClient(Protocol):
    def send(self, payload: dict, idempotency_key: str) -> str: ...


class ResendClient:
    def __init__(self, config: Settings) -> None:
        self.config = config

    def send(self, payload: dict, idempotency_key: str) -> str:
        key = self.config.resend_api_key.get_secret_value()
        if not key or not payload.get("from"):
            raise ConfigurationError("Configure RESEND_API_KEY and EMAIL_FROM (or sender_email)")
        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={"Authorization": f"Bearer {key}", "Idempotency-Key": idempotency_key},
                timeout=15,
            )
            response.raise_for_status()
            message_id = response.json()["id"]
            if not isinstance(message_id, str) or not message_id:
                raise ValueError("Missing message ID")
            return message_id
        except httpx.HTTPStatusError as exc:
            response = exc.response
            logger.error(
                "Resend API rejected email with status %s: %s",
                response.status_code,
                response.text,
            )
            raise IntegrationError(
                "Resend did not confirm email acceptance; delivery can be retried"
            ) from exc
        except httpx.HTTPError as exc:
            logger.exception("Resend HTTP request failed: %s", exc)
            raise IntegrationError(
                "Resend did not confirm email acceptance; delivery can be retried"
            ) from exc
        except (ValueError, KeyError) as exc:
            logger.exception("Resend response parsing failed: %s", exc)
            raise IntegrationError(
                "Resend did not confirm email acceptance; delivery can be retried"
            ) from exc
