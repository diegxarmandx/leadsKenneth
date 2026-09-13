from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from sqlalchemy import func, select

from app.core.exceptions import ConfigurationError, InsufficientInventoryError, IntegrationError
from app.db.session import write_session
from app.models import AuditLog, Lead, PricingRule, Purchase, PurchaseLead
from app.models.enums import PurchaseStatus
from app.repositories.purchase_repository import PurchaseRepository
from app.schemas.pricing import PricingRulePatch
from app.services.fulfillment_service import FulfillmentService
from app.services.pricing_service import PricingService
from tests.conftest import checkout_event, exclusion, request_data, send_event


def test_checkout_computes_total_and_reserves_nothing(env, add_lead):
    for _ in range(3):
        add_lead()
    order = env.runtime.purchases().create_checkout(request_data(quantity=3))
    with env.factory() as session:
        saved = PurchaseRepository(session).by_public_id(order.public_id)
        assert saved.total_amount_cents == 6000 and saved.status == PurchaseStatus.PENDING
        assert saved.stripe_checkout_id == order.checkout_session_id
        assert session.scalar(select(func.count()).select_from(PurchaseLead)) == 0
    assert env.stripe.calls[0].total_amount_cents == 6000


def test_checkout_shortage_never_calls_stripe(env):
    with pytest.raises(InsufficientInventoryError):
        env.runtime.purchases().create_checkout(request_data())
    assert not env.stripe.calls
    with env.factory() as session:
        assert session.scalar(select(func.count()).select_from(Purchase)) == 0


def test_unconfigured_checkout_fails_gracefully_without_allocating(env, add_lead):
    add_lead()
    env.stripe.error = ConfigurationError("Configure STRIPE_SECRET_KEY")
    response = env.client.post("/api/v1/checkout", json=request_data().model_dump())
    assert response.status_code == 503
    with env.factory() as session:
        assert session.scalar(select(Purchase)).status == PurchaseStatus.FAILED
        assert session.scalar(select(func.count()).select_from(PurchaseLead)) == 0


@pytest.mark.parametrize(
    "kind", ["checkout.session.async_payment_failed", "checkout.session.expired"]
)
def test_failed_payment_allocates_nothing(env, add_lead, kind):
    add_lead()
    order = env.runtime.purchases().create_checkout(request_data())
    assert send_event(env, checkout_event(order, kind, payment_status="unpaid")).status_code == 200
    with env.factory() as session:
        assert session.scalar(select(Purchase)).status == PurchaseStatus.FAILED
        assert session.scalar(select(func.count()).select_from(PurchaseLead)) == 0


def test_exact_fulfillment_uses_only_eligible_leads_and_saves_history(env, add_lead):
    eligible = {add_lead() for _ in range(5)}
    add_lead(age=1)
    add_lead(source_active=False)
    add_lead(municipality="Ponce")
    excluded = add_lead()
    exclusion(env, excluded, env.now + timedelta(days=1))
    order = env.runtime.purchases().create_checkout(request_data(quantity=3))
    service = FulfillmentService(env.factory, env.config)
    service.payment_succeeded(checkout_event(order, amount_total=6000)["data"]["object"], env.now)
    with env.factory() as session:
        saved = PurchaseRepository(session).by_public_id(order.public_id, with_leads=True)
        assert saved.status == PurchaseStatus.FULFILLED and saved.fulfilled_at == env.now
        assert len(saved.purchase_leads) == 3
        assert {item.lead_id for item in saved.purchase_leads} <= eligible
        for item in saved.purchase_leads:
            assert item.price_paid_cents == 2000 and item.pricing_rule_id == 2
            assert item.excluded_until == env.now + timedelta(days=20)
    with write_session(env.factory) as session:
        PricingService(session).update(2, PricingRulePatch(price_cents=1800, exclusion_days=3))
    with env.factory() as session:
        saved = PurchaseRepository(session).by_public_id(order.public_id, with_leads=True)
        assert all(item.price_paid_cents == 2000 for item in saved.purchase_leads)
        assert all(
            item.excluded_until == env.now + timedelta(days=20) for item in saved.purchase_leads
        )


def test_duplicate_webhooks_do_not_reallocate_or_resend(env, add_lead):
    for _ in range(3):
        add_lead()
    order = env.runtime.purchases().create_checkout(request_data())
    event = checkout_event(order)
    assert send_event(env, event).status_code == 200
    event["id"] = "evt_different_id_same_purchase"
    assert send_event(env, event).status_code == 200
    with env.factory() as session:
        assert session.scalar(select(func.count()).select_from(PurchaseLead)) == 1
        assert session.scalar(select(Purchase)).email_sent_at is not None
    assert len(env.email.calls) == 1


def test_delayed_payment_waits_for_success_and_late_failure_does_not_regress(env, add_lead):
    add_lead()
    order = env.runtime.purchases().create_checkout(request_data())
    assert send_event(env, checkout_event(order, payment_status="unpaid")).status_code == 200
    assert env.runtime.purchases().get_public(order.public_id).status == PurchaseStatus.PENDING
    assert (
        send_event(
            env, checkout_event(order, "checkout.session.async_payment_succeeded")
        ).status_code
        == 200
    )
    assert (
        send_event(env, checkout_event(order, "checkout.session.async_payment_failed")).status_code
        == 200
    )
    assert env.runtime.purchases().get_public(order.public_id).status == PurchaseStatus.FULFILLED


@pytest.mark.parametrize("change", ["shortage", "price_change", "age_transition"])
def test_post_payment_failure_never_partially_fulfills(env, add_lead, change):
    ids = [add_lead() for _ in range(3)]
    order = env.runtime.purchases().create_checkout(request_data(quantity=3))
    with write_session(env.factory) as session:
        if change == "shortage":
            session.get(Lead, ids[0]).source_active = False
        elif change == "price_change":
            session.get(PricingRule, 2).price_cents = 1800
        else:
            for lead_id in ids:
                session.get(Lead, lead_id).lead_date = env.today - timedelta(days=31)
    event = checkout_event(order, amount_total=6000)
    assert send_event(env, event).status_code == 200
    with env.factory() as session:
        saved = session.scalar(select(Purchase))
        assert saved.status == PurchaseStatus.FULFILLMENT_FAILED
        assert saved.paid_at is not None and saved.stripe_payment_intent
        assert saved.fulfilled_at is None
        assert session.scalar(select(func.count()).select_from(PurchaseLead)) == 0
        assert session.scalar(select(AuditLog).where(AuditLog.action == "fulfillment.failed"))
    add_lead()
    assert send_event(env, event).status_code == 200
    assert (
        env.runtime.purchases().get_public(order.public_id).status
        == PurchaseStatus.FULFILLMENT_FAILED
    )
    assert not env.email.calls


@pytest.mark.parametrize(
    "changes", [{"amount_total": 1}, {"currency": "eur"}, {"mode": "subscription"}]
)
def test_payment_details_mismatch_is_flagged_without_allocation(env, add_lead, changes):
    add_lead()
    order = env.runtime.purchases().create_checkout(request_data())
    assert send_event(env, checkout_event(order, **changes)).status_code == 200
    assert (
        env.runtime.purchases().get_public(order.public_id).status
        == PurchaseStatus.FULFILLMENT_FAILED
    )
    assert not env.email.calls


def test_email_failure_preserves_fulfillment_and_webhook_retry_only_retries_email(env, add_lead):
    add_lead(first_name="<script>unsafe</script>")
    order = env.runtime.purchases().create_checkout(request_data())
    env.email.error = IntegrationError("Email temporarily unavailable")
    event = checkout_event(order)
    assert send_event(env, event).status_code == 502
    saved = env.runtime.purchases().get_public(order.public_id)
    assert saved.status == PurchaseStatus.FULFILLED and saved.email_sent_at is None
    env.email.error = None
    assert send_event(env, event).status_code == 200
    assert env.email.calls[0][1] == env.email.calls[1][1]
    assert "<script>" not in env.email.calls[1][0]["html"]
    with env.factory() as session:
        assert session.scalar(select(func.count()).select_from(PurchaseLead)) == 1
        assert session.scalar(select(Purchase)).email_sent_at is not None


def test_allocation_insert_failure_rolls_back_entire_transaction(env, add_lead, monkeypatch):
    for _ in range(2):
        add_lead()
    order = env.runtime.purchases().create_checkout(request_data(quantity=2))
    original = PurchaseRepository.add_allocation
    calls = 0

    def fail(self, **values):
        nonlocal calls
        calls += 1
        original(self, **values)
        self.session.flush()
        if calls == 2:
            raise RuntimeError("simulated write failure")

    monkeypatch.setattr(PurchaseRepository, "add_allocation", fail)
    with pytest.raises(RuntimeError):
        FulfillmentService(env.factory, env.config).payment_succeeded(
            checkout_event(order, amount_total=4000)["data"]["object"],
            env.now,
        )
    with env.factory() as session:
        assert session.scalar(select(func.count()).select_from(PurchaseLead)) == 0
        assert session.scalar(select(Purchase)).status == PurchaseStatus.PENDING


@pytest.mark.parametrize("same_order", [True, False])
def test_concurrent_fulfillment_serializes_eligibility_and_order_state(env, add_lead, same_order):
    add_lead()
    first = env.runtime.purchases().create_checkout(request_data())
    second = first if same_order else env.runtime.purchases().create_checkout(request_data())
    barrier = Barrier(2)

    def fulfill(order):
        barrier.wait(timeout=10)
        return FulfillmentService(env.factory, env.config).payment_succeeded(
            checkout_event(order)["data"]["object"],
            env.now,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(fulfill, order) for order in (first, second)]
        for future in futures:
            future.result(timeout=20)
    with env.factory() as session:
        assert session.scalar(select(func.count()).select_from(PurchaseLead)) == 1
        statuses = list(session.scalars(select(Purchase.status)))
        assert statuses.count(PurchaseStatus.FULFILLED) == 1
        if not same_order:
            assert statuses.count(PurchaseStatus.FULFILLMENT_FAILED) == 1
