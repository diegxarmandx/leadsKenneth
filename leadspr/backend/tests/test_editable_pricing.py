import pytest
from sqlalchemy import select

from app.models import PurchaseLead
from tests.conftest import checkout_event, request_data, send_event


@pytest.mark.parametrize("price", [0, -100, 22.5, "2250", "22.501", True, None, {}, []])
def test_price_patch_rejects_invalid_cents_without_mutation(env, price):
    response = env.client.patch(
        "/api/v1/admin/pricing-rules/2", json={"price_cents": price}, headers=env.admin
    )
    assert response.status_code == 422
    rules = env.client.get("/api/v1/admin/pricing-rules", headers=env.admin).json()
    assert next(rule for rule in rules if rule["id"] == 2)["price_cents"] == 2000


def test_price_patch_requires_admin_and_keeps_four_distinct_tiers(env):
    url = "/api/v1/admin/pricing-rules/2"
    assert env.client.patch(url, json={"price_cents": 2250}).status_code == 401
    response = env.client.patch(url, json={"price_cents": 3000}, headers=env.admin)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "pricing_rule_conflict"
    assert len(env.client.get("/api/v1/inventory/summary").json()["tiers"]) == 4


def test_edit_price_drives_inventory_checkout_and_preserves_fulfilled_history(env, add_lead):
    for _ in range(4):
        add_lead(age=12)
    url = "/api/v1/admin/pricing-rules/2"
    result = env.client.patch(url, json={"price_cents": 2250}, headers=env.admin)
    assert result.status_code == 200
    rule = result.json()
    assert (rule["min_age_days"], rule["max_age_days"], rule["exclusion_days"]) == (8, 30, 20)
    tiers = env.client.get("/api/v1/inventory/summary").json()["tiers"]
    recent = next(tier for tier in tiers if tier["age_ranges"][0]["min_age_days"] == 8)
    assert recent["price_cents"] == 2250 and recent["available_quantity"] == 4
    # Old or forged prices never reach Stripe or create a purchase.
    for price in [2000, 1, 2249]:
        response = env.client.post("/api/v1/checkout", json=request_data(price=price).model_dump())
        assert response.status_code == 400
    assert not env.stripe.calls
    response = env.client.post(
        "/api/v1/checkout", json=request_data(quantity=2, price=2250).model_dump()
    )
    assert response.status_code == 201
    public_id = response.json()["public_id"]
    sent_to_stripe = env.stripe.calls[-1]
    assert sent_to_stripe.price_per_lead_cents == 2250
    assert sent_to_stripe.total_amount_cents == 4500
    assert send_event(env, checkout_event(sent_to_stripe, amount_total=4500)).status_code == 200
    assert env.client.patch(url, json={"price_cents": 2400}, headers=env.admin).status_code == 200
    order = env.client.get(f"/api/v1/purchases/{public_id}").json()
    assert order["status"] == "FULFILLED"
    assert order["price_per_lead_cents"] == 2250 and order["total_amount_cents"] == 4500
    with env.factory() as session:
        allocations = list(session.scalars(select(PurchaseLead)))
        assert len(allocations) == 2
        assert all(
            item.price_paid_cents == 2250 and item.pricing_rule_id == 2 for item in allocations
        )
    dashboard = env.client.get("/api/v1/admin/dashboard", headers=env.admin).json()
    assert dashboard["recent_purchases"][0]["total_amount_cents"] == 4500
    assert dashboard["stats"]["revenue_cents"] == 4500
