import logging
import re
from typing import Protocol

import httpx

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, EmailDeliveryBlocked, IntegrationError

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
            try:
                body = response.json()
                name = body.get("name", "") if isinstance(body, dict) else ""
            except ValueError:
                name = ""
            reason = (
                name
                if isinstance(name, str) and re.fullmatch(r"[a-z_]{1,80}", name)
                else "provider_rejected"
            )
            # Validation/auth/recipient rejections cannot succeed unchanged.
            # 408, concurrent 409, 429 and 5xx remain retryable.
            if response.status_code in {400, 401, 403, 404, 405, 413, 422} or (
                response.status_code == 409 and reason == "invalid_idempotent_request"
            ):
                raise EmailDeliveryBlocked(
                    provider_status=response.status_code, reason=reason
                ) from exc
            logger.error(
                "Resend API rejected email with status %s (%s)",
                response.status_code,
                reason,
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
