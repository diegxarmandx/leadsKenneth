from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy import func, select

from app.core.exceptions import IntegrationError
from app.db.session import write_session
from app.models import AuditLog, PurchaseLead
from app.services.checkout_reconciliation_service import ATTEMPT
from tests.conftest import checkout_event, request_data, send_event


def paid_order(env, add_lead):
    add_lead()
    order = env.runtime.purchases().create_checkout(request_data())
    env.stripe.sessions[order.checkout_session_id] = checkout_event(order, status="complete")[
        "data"
    ]["object"]
    return order


def allow_retry(env):
    with write_session(env.factory) as session:
        for log in session.scalars(select(AuditLog).where(AuditLog.action == ATTEMPT)):
            log.created_at -= timedelta(minutes=1)


def test_return_recovers_missing_webhook_and_replays_do_not_duplicate(env, add_lead):
    order = paid_order(env, add_lead)
    url = f"/api/v1/purchases/{order.public_id}"
    assert env.client.get(url).json()["status"] == "PENDING"
    assert not env.email.calls  # GET remains read-only.
    response = env.client.post(f"{url}/refresh")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "FULFILLED" and data["email_sent_at"]
    assert not {"buyer_email", "stripe_checkout_id", "stripe_payment_intent"} & data.keys()
    assert env.client.post(f"{url}/refresh").status_code == 200
    assert send_event(env, checkout_event(order)).status_code == 200
    assert len(env.email.calls) == 1
    with env.factory() as session:
        assert session.scalar(select(func.count()).select_from(PurchaseLead)) == 1


@pytest.mark.parametrize(
    "status,payment,expected",
    [
        ("open", "unpaid", "PENDING"),
        ("complete", "unpaid", "PENDING"),
        ("expired", "unpaid", "FAILED"),
    ],
)
def test_unpaid_orders_never_allocate_even_with_forged_browser_body(
    env, add_lead, status, payment, expected
):
    order = paid_order(env, add_lead)
    env.stripe.sessions[order.checkout_session_id].update(status=status, payment_status=payment)
    response = env.client.post(
        f"/api/v1/purchases/{order.public_id}/refresh",
        json={
            "payment_status": "paid",
            "status": "complete",
            "checkout_id": "cs_forged",
        },
    )
    assert response.json()["status"] == expected
    assert not env.email.calls
    with env.factory() as session:
        assert session.scalar(select(func.count()).select_from(PurchaseLead)) == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "cs_other"),
        ("client_reference_id", "ORD-OTHER0001"),
        ("metadata", {"purchase_public_id": "ORD-OTHER0001"}),
    ],
)
def test_retrieved_session_must_match_the_stored_order(env, add_lead, field, value):
    order = paid_order(env, add_lead)
    env.stripe.sessions[order.checkout_session_id][field] = value
    response = env.client.post(f"/api/v1/purchases/{order.public_id}/refresh")
    assert response.status_code == 400
    assert env.runtime.purchases().get_public(order.public_id).status.value == "PENDING"
    assert not env.email.calls


def test_provider_failure_is_visible_and_refreshes_are_throttled(env, add_lead, monkeypatch):
    order = paid_order(env, add_lead)
    retrieve = MagicMock(side_effect=IntegrationError("Stripe unavailable"))
    monkeypatch.setattr(env.stripe, "retrieve_checkout", retrieve)
    url = f"/api/v1/purchases/{order.public_id}/refresh"
    assert env.client.post(url).status_code == 502
    assert env.client.post(url).json()["status"] == "PENDING"
    assert retrieve.call_count == 1
    allow_retry(env)
    assert env.client.post(url).status_code == 502
    assert retrieve.call_count == 2
    assert not env.email.calls


def test_background_recovery_retries_email_without_reallocating(env, add_lead):
    order = paid_order(env, add_lead)
    env.email.error = IntegrationError("Provider rejected email")
    response = env.client.post(f"/api/v1/purchases/{order.public_id}/refresh")
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "email_delivery_pending"
    assert env.runtime.purchases().get_public(order.public_id).status.value == "FULFILLED"
    env.email.error = None
    allow_retry(env)
    env.runtime.reconciliation().recover_pending()
    assert env.runtime.purchases().get_public(order.public_id).email_sent_at
    assert len(env.email.calls) == 2
    assert env.email.calls[0][1] == env.email.calls[1][1]
    with env.factory() as session:
        assert session.scalar(select(func.count()).select_from(PurchaseLead)) == 1
        assert session.scalar(select(AuditLog).where(AuditLog.action == "email.accepted"))


def test_background_recovery_fulfills_without_browser_return(env, add_lead):
    order = paid_order(env, add_lead)
    env.runtime.reconciliation().recover_pending()
    assert env.runtime.purchases().get_public(order.public_id).email_sent_at
    assert len(env.email.calls) == 1


def test_parallel_recovery_and_webhook_deliver_once(env, add_lead):
    order = paid_order(env, add_lead)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [
            pool.submit(env.runtime.reconciliation().refresh, order.public_id) for _ in range(2)
        ]
        futures.append(pool.submit(env.runtime.webhooks().process, *signed_payload(order)))
        for future in futures:
            future.result(timeout=10)
    assert len(env.email.calls) == 1
    with env.factory() as session:
        assert session.scalar(select(func.count()).select_from(PurchaseLead)) == 1


def signed_payload(order):
    import hashlib
    import hmac
    import json
    import time

    from tests.conftest import TEST_WEBHOOK_SECRET

    payload = json.dumps(checkout_event(order)).encode()
    timestamp = int(time.time())
    digest = hmac.new(
        TEST_WEBHOOK_SECRET.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return payload, f"t={timestamp},v1={digest}"
