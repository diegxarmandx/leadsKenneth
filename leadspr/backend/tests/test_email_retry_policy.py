import logging

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import func, select

from app.core.exceptions import EmailDeliveryBlocked, IntegrationError
from app.integrations.email.client import ResendClient
from app.models import AuditLog, PurchaseLead
from app.services.email_service import EmailService
from tests.conftest import checkout_event, send_event
from tests.test_checkout_reconciliation import paid_order


@pytest.mark.parametrize(
    "status,name",
    [
        (400, "validation_error"),
        (401, "restricted_api_key"),
        (403, "validation_error"),
        (422, "validation_error"),
        (409, "invalid_idempotent_request"),
    ],
)
def test_permanent_resend_rejections_are_classified_without_logging_recipient(
    env, monkeypatch, caplog, status, name
):
    def reject(url, **kwargs):
        return httpx.Response(
            status,
            json={
                "name": name,
                "message": "Sensitive recipient: private@example.com",
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("app.integrations.email.client.httpx.post", reject)
    config = env.config.model_copy(update={"resend_api_key": SecretStr("fake-test-key")})
    with caplog.at_level(logging.ERROR), pytest.raises(EmailDeliveryBlocked) as error:
        ResendClient(config).send({"from": "sender@example.com"}, "delivery/test")
    assert error.value.provider_status == status
    assert error.value.reason == name
    assert "private@example.com" not in caplog.text
    assert "private@example.com" not in str(error.value)


@pytest.mark.parametrize(
    "status,name",
    [
        (408, "timeout"),
        (409, "concurrent_idempotent_requests"),
        (409, "resource_locked"),
        (429, "rate_limit_exceeded"),
        (500, "application_error"),
        (503, "service_unavailable"),
    ],
)
def test_temporary_resend_rejections_remain_retryable(env, monkeypatch, status, name):
    def reject(url, **kwargs):
        return httpx.Response(status, json={"name": name}, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.integrations.email.client.httpx.post", reject)
    config = env.config.model_copy(update={"resend_api_key": SecretStr("fake-test-key")})
    with pytest.raises(IntegrationError) as error:
        ResendClient(config).send({"from": "sender@example.com"}, "delivery/test")
    assert not isinstance(error.value, EmailDeliveryBlocked)


@pytest.mark.parametrize("status", [403, 422])
def test_permanent_delivery_block_survives_service_restart_and_scheduler_sweeps(
    env, add_lead, caplog, status
):
    order = paid_order(env, add_lead)
    env.email.error = EmailDeliveryBlocked(provider_status=status, reason="validation_error")
    with caplog.at_level(logging.WARNING):
        env.runtime.reconciliation().recover_pending()
        first_logs = len(caplog.records)
        for _ in range(3):
            env.runtime.reconciliation().recover_pending()
            assert send_event(env, checkout_event(order)).status_code == 200
        response = env.client.post(f"/api/v1/purchases/{order.public_id}/refresh")
        assert response.status_code == 502
        assert response.json()["error"]["code"] == "email_delivery_blocked"
        with pytest.raises(EmailDeliveryBlocked):
            EmailService(env.factory, env.config, env.email).deliver(order.public_id)
        assert len(caplog.records) == first_logs  # No repeated provider/recovery errors.
    assert len(env.email.calls) == 1
    saved = env.runtime.purchases().get_public(order.public_id)
    assert saved.status.value == "FULFILLED" and saved.email_sent_at is None
    with env.factory() as session:
        assert session.scalar(select(func.count()).select_from(PurchaseLead)) == 1
        blocks = list(session.scalars(select(AuditLog).where(AuditLog.action == "email.blocked")))
        assert len(blocks) == 1 and str(status) in blocks[0].new_values


def test_admin_can_retry_after_correction_but_public_cannot_bypass_block(env, add_lead):
    order = paid_order(env, add_lead)
    env.email.error = EmailDeliveryBlocked(provider_status=403)
    env.runtime.reconciliation().recover_pending()
    url = f"/api/v1/admin/purchases/{order.public_id}/resend-email"
    assert env.client.post(url, headers={"Idempotency-Key": "corrected-email-1"}).status_code == 401
    env.email.error = IntegrationError("temporary connection failure during admin retry")
    assert (
        env.client.post(
            url, headers=env.admin | {"Idempotency-Key": "corrected-email-1"}
        ).status_code
        == 502
    )
    env.runtime.reconciliation().recover_pending()
    assert len(env.email.calls) == 2  # Admin failure did not silently unblock automation.
    env.email.error = None
    headers = env.admin | {"Idempotency-Key": "corrected-email-1"}
    assert env.client.post(url, headers=headers).json() == {"sent": True}
    assert env.client.post(url, headers=headers).json() == {"sent": True}
    env.runtime.reconciliation().recover_pending()
    assert len(env.email.calls) == 3
    assert env.runtime.purchases().get_public(order.public_id).email_sent_at
    with env.factory() as session:
        assert not session.scalar(select(EmailService.blocked_query(order.public_id)))
        assert session.scalar(select(func.count()).select_from(PurchaseLead)) == 1
