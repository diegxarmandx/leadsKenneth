import json

import pytest
from sqlalchemy import func, select

from app.models import AuditLog, Lead
from tests.conftest import checkout_event, request_data, send_event


def test_health_and_cors(env):
    assert env.client.get("/api/v1/health").json() == {"status": "ok", "database": "ok"}
    headers = {"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"}
    assert env.client.options("/api/v1/checkout", headers=headers).status_code == 200
    headers["Origin"] = "https://untrusted.example"
    assert env.client.options("/api/v1/checkout", headers=headers).status_code == 400


@pytest.mark.parametrize("path", ["leads", "pricing-rules", "sync-runs", "purchases", "settings"])
def test_admin_requires_authentication(env, path):
    assert env.client.get(f"/api/v1/admin/{path}").status_code == 401
    assert env.client.get(f"/api/v1/admin/{path}", headers=env.admin).status_code == 200


def test_public_responses_do_not_expose_pii_or_internal_ids(env, add_lead):
    add_lead(first_name="PrivateName", phone="7875550199")
    order = env.runtime.purchases().create_checkout(request_data())
    send_event(env, checkout_event(order))
    inventory = env.client.get("/api/v1/inventory/summary").text
    response = env.client.get(f"/api/v1/purchases/{order.public_id}")
    data = response.json()
    for secret in ("PrivateName", "7875550199", "buyer@example.com", "lead@example.com"):
        assert secret not in inventory and secret not in response.text
    assert not ({"id", "buyer_name", "buyer_email", "leads", "stripe_payment_intent"} & data.keys())
    assert response.headers["Cache-Control"] == "no-store"


def test_checkout_rejects_frontend_totals_and_invalid_quantity(env):
    data = request_data().model_dump() | {"total_amount_cents": 1}
    assert env.client.post("/api/v1/checkout", json=data).status_code == 422
    for quantity in (0, -1, 1.5, True):
        data = request_data().model_dump() | {"quantity": quantity}
        assert env.client.post("/api/v1/checkout", json=data).status_code == 422
    assert not env.stripe.calls


def test_signature_verification_rejects_tampering(env):
    response = env.client.post(
        "/api/v1/webhooks/stripe", content=b"{}", headers={"Stripe-Signature": "t=1,v1=invalid"}
    )
    assert response.status_code == 400 and response.json()["error"]["code"] == "invalid_input"
    assert (
        send_event(
            env, {"id": "evt_ignored", "type": "unknown", "data": {"object": {}}}
        ).status_code
        == 200
    )


def test_mismatched_checkout_id_cannot_fulfill(env, add_lead):
    add_lead()
    order = env.runtime.purchases().create_checkout(request_data())
    assert send_event(env, checkout_event(order, id="cs_other")).status_code == 400
    assert not env.email.calls


def test_pricing_and_settings_changes_are_audited_and_secrets_rejected(env):
    response = env.client.patch(
        "/api/v1/admin/pricing-rules/2", json={"price_cents": 1800}, headers=env.admin
    )
    assert response.status_code == 200
    assert response.json()["price_cents"] == 1800
    response = env.client.patch(
        "/api/v1/admin/settings", json={"company_name": "Example"}, headers=env.admin
    )
    assert response.status_code == 200 and response.json()["company_name"] == "Example"
    assert (
        env.client.patch(
            "/api/v1/admin/settings", json={"STRIPE_SECRET_KEY": "secret"}, headers=env.admin
        ).status_code
        == 400
    )
    with env.factory() as session:
        logs = list(session.scalars(select(AuditLog)))
        assert {log.action for log in logs} == {"pricing_rule.updated", "setting.updated"}
        pricing = next(log for log in logs if log.action == "pricing_rule.updated")
        assert json.loads(pricing.old_values)["price_cents"] == 2000
        assert json.loads(pricing.new_values)["price_cents"] == 1800


def test_admin_details_filters_and_resend(env, add_lead):
    add_lead()
    order = env.runtime.purchases().create_checkout(request_data())
    send_event(env, checkout_event(order))
    response = env.client.get(
        "/api/v1/admin/leads?price_cents=2000&min_age_days=8", headers=env.admin
    )
    assert response.status_code == 200 and response.json()["total"] == 1
    assert response.json()["items"][0]["currently_excluded"] is True
    response = env.client.get(f"/api/v1/admin/purchases/{order.public_id}", headers=env.admin)
    assert response.json()["leads"][0]["price_paid_cents"] == 2000
    headers = env.admin | {"Idempotency-Key": "test-resend-key"}
    assert (
        env.client.post(
            f"/api/v1/admin/purchases/{order.public_id}/resend-email", headers=headers
        ).status_code
        == 200
    )
    assert len(env.email.calls) == 2
    repeated = env.client.post(
        f"/api/v1/admin/purchases/{order.public_id}/resend-email",
        headers=headers,
    )
    assert repeated.status_code == 200 and len(env.email.calls) == 2
    assert (
        env.client.get("/api/v1/admin/purchases?status=FULFILLED", headers=env.admin).json()[
            "total"
        ]
        == 1
    )
    assert (
        env.client.get(
            "/api/v1/admin/purchases?created_from=2026-01-01T00:00:00", headers=env.admin
        ).status_code
        == 422
    )


def test_seed_is_idempotent_and_never_adds_leads(env):
    from app.db.session import write_session
    from app.models import AppSetting, PricingRule
    from scripts.seed import seed

    with write_session(env.factory) as session:
        seed(session, env.config)
        seed(session, env.config)
        assert session.scalar(select(func.count()).select_from(PricingRule)) == 4
        assert session.scalar(select(func.count()).select_from(Lead)) == 0
        assert session.scalar(select(func.count()).select_from(AppSetting)) == 6
