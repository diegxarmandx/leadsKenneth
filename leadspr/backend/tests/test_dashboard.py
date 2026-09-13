from datetime import timedelta

from app.db.session import write_session
from app.models import Purchase
from app.models.enums import PurchaseStatus
from tests.conftest import exclusion


def test_dashboard_totals_use_all_orders_and_current_eligibility(env, add_lead):
    add_lead()
    excluded = add_lead()
    exclusion(env, excluded, env.now + timedelta(days=1))
    add_lead(source_active=False)
    add_lead(age=-1)
    with write_session(env.factory) as session:
        for i in range(12):
            session.add(
                Purchase(
                    public_id=f"ORD-TEST-{i}",
                    buyer_name="Test Buyer",
                    buyer_email="buyer@example.com",
                    requested_quantity=2,
                    price_per_lead_cents=2000,
                    total_amount_cents=4000,
                    status=PurchaseStatus.FULFILLED if i < 10 else PurchaseStatus.FAILED,
                )
            )
    assert env.client.get("/api/v1/admin/dashboard").status_code == 401
    result = env.client.get("/api/v1/admin/dashboard", headers=env.admin)
    assert result.status_code == 200
    data = result.json()
    assert data["stats"] == {
        "active_leads": 3,
        "available_inventory": 1,
        "fulfilled_orders": 11,
        "revenue_cents": 42000,
    }
    assert len(data["recent_purchases"]) == 8
    assert len(data["pricing_rules"]) == 4
    assert data["last_sync"] is None
    assert "buyer@example.com" not in result.text
    assert "stripe_payment_intent" not in result.text


def test_checkout_mode_exposes_only_safe_metadata(env):
    assert env.client.get("/api/v1/checkout/config").json() == {"payment_mode": "unconfigured"}
    from pydantic import SecretStr

    for prefix, mode in [("sk_test_", "test"), ("rk_test_", "test"), ("sk_live_", "live")]:
        env.config.stripe_secret_key = SecretStr(prefix + "never_expose_this")
        response = env.client.get("/api/v1/checkout/config")
        assert response.json() == {"payment_mode": mode}
        assert "never_expose" not in response.text
