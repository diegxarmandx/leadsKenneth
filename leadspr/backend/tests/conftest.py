import hashlib
import hmac
import json
import time
from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.db.base import Base
from app.db.session import write_session
from app.integrations.stripe.client import CheckoutSession, StripeClient
from app.main import create_app
from app.models import Lead, Purchase, PurchaseLead
from app.models.enums import PurchaseStatus
from app.schemas.purchase import CheckoutRequest
from app.utils.time import business_date, utcnow
from scripts.seed import seed

TEST_WEBHOOK_SECRET = "whsec_local_test_only"
TEST_ADMIN_TOKEN = "local-test-admin-token-with-32-characters"


class FakeSheets:
    def __init__(self):
        self.rows = []
        self.error = None
        self.append_error = None
        self.append_calls = []

    def fetch_rows(self, sheet_id, tab):
        if self.error:
            raise self.error
        return self.rows

    def append_lead(self, sheet_id, tab, lead):
        if self.append_error:
            raise self.append_error
        if any(row["external_id"] == lead.external_id for row in self.rows):
            return False
        self.append_calls.append((sheet_id, tab, lead))
        self.rows.append(lead.model_dump(mode="json"))
        return True


class FakeStripe:
    def __init__(self, config):
        self.real = StripeClient(config)
        self.calls = []
        self.error = None
        self.sessions = {}

    def create_checkout(self, purchase):
        self.calls.append(purchase)
        if self.error:
            raise self.error
        self.sessions[f"cs_{purchase.public_id}"] = {"status": "open", "payment_status": "unpaid"}
        return CheckoutSession(f"cs_{purchase.public_id}", "https://checkout.stripe.com/test")

    def retrieve_checkout(self, checkout_id):
        if self.error:
            raise self.error
        return self.sessions[checkout_id]

    def verify_event(self, payload, signature):
        return self.real.verify_event(payload, signature)


class FakeEmail:
    def __init__(self):
        self.calls = []
        self.error = None

    def send(self, payload, idempotency_key):
        self.calls.append((payload, idempotency_key))
        if self.error:
            raise self.error
        return "email_test"


@pytest.fixture
def env(tmp_path):
    config = Settings(
        _env_file=None,
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        scheduler_enabled=False,
        admin_api_token=SecretStr(TEST_ADMIN_TOKEN),
        stripe_secret_key=SecretStr(""),
        stripe_webhook_secret=SecretStr(TEST_WEBHOOK_SECRET),
        google_sheets_credentials_json=SecretStr(""),
        google_sheet_id="test-sheet",
        resend_api_key=SecretStr(""),
        email_from="orders@example.com",
    )
    sheets, stripe, email = FakeSheets(), FakeStripe(config), FakeEmail()
    app = create_app(config, sheets=sheets, checkout=stripe, email=email)
    runtime = app.state.runtime
    with runtime.sessions() as session:
        Base.metadata.create_all(session.get_bind())
    with write_session(runtime.sessions) as session:
        seed(session, config)
    now = utcnow()
    with TestClient(app) as client:
        yield SimpleNamespace(
            config=config,
            runtime=runtime,
            factory=runtime.sessions,
            sheets=sheets,
            stripe=stripe,
            email=email,
            client=client,
            now=now,
            today=business_date(config.app_timezone, now),
            admin={"Authorization": f"Bearer {TEST_ADMIN_TOKEN}"},
        )


@pytest.fixture
def add_lead(env):
    counter = 0

    def create(age=10, **values):
        nonlocal counter
        counter += 1
        defaults = {
            "external_id": f"lead-{counter}",
            "lead_date": env.today - timedelta(days=age),
            "first_name": "Test",
            "last_name": "Lead",
            "phone": "7875550100",
            "email": "lead@example.com",
            "municipality": "Bayamón",
            "insurance_type": "Life Insurance",
            "source_active": True,
        }
        with write_session(env.factory) as session:
            lead = Lead(**(defaults | values))
            session.add(lead)
            session.flush()
            return lead.id

    return create


def request_data(quantity=1, price=2000, **kwargs):
    return CheckoutRequest(
        buyer_name="Buyer",
        buyer_email="buyer@example.com",
        municipality="Bayamón",
        price_per_lead_cents=price,
        quantity=quantity,
        **kwargs,
    )


def checkout_event(order, kind="checkout.session.completed", **overrides):
    data = {
        "id": f"cs_{order.public_id}",
        "object": "checkout.session",
        "mode": "payment",
        "metadata": {"purchase_public_id": order.public_id},
        "client_reference_id": order.public_id,
        "payment_status": "paid",
        "currency": "usd",
        "payment_intent": f"pi_{order.public_id}",
        "amount_total": 2000,
    }
    data.update(overrides)
    return {
        "id": f"evt_{order.public_id}",
        "object": "event",
        "type": kind,
        "data": {"object": data},
    }


def send_event(env, event):
    payload = json.dumps(event).encode()
    timestamp = int(time.time())
    digest = hmac.new(
        TEST_WEBHOOK_SECRET.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return env.client.post(
        "/api/v1/webhooks/stripe",
        content=payload,
        headers={
            "Stripe-Signature": f"t={timestamp},v1={digest}",
            "Content-Type": "application/json",
        },
    )


def exclusion(env, lead_id, until):
    with write_session(env.factory) as session:
        purchase = Purchase(
            public_id=f"OLD-{lead_id}",
            buyer_name="Past",
            buyer_email="past@example.com",
            requested_quantity=1,
            price_per_lead_cents=2000,
            total_amount_cents=2000,
            status=PurchaseStatus.FULFILLED,
        )
        session.add(purchase)
        session.flush()
        session.add(
            PurchaseLead(
                purchase_id=purchase.id,
                lead_id=lead_id,
                pricing_rule_id=2,
                price_paid_cents=2000,
                purchased_at=env.now - timedelta(days=30),
                excluded_until=until,
            )
        )
