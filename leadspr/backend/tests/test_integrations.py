from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from pydantic import SecretStr

from app.core.exceptions import ConfigurationError, IntegrationError
from app.integrations.email.client import ResendClient
from app.integrations.google_sheets.client import GoogleSheetsClient
from app.integrations.stripe.client import StripeClient
from tests.conftest import request_data


def test_stripe_checkout_adapter_builds_server_owned_amounts(env, add_lead, monkeypatch):
    add_lead()
    env.runtime.purchases().create_checkout(request_data())
    purchase = env.stripe.calls[0]
    create = MagicMock(
        return_value=SimpleNamespace(id="cs_contract", url="https://checkout.stripe.com/example")
    )
    sdk = SimpleNamespace(
        v1=SimpleNamespace(checkout=SimpleNamespace(sessions=SimpleNamespace(create=create)))
    )
    constructor = MagicMock(return_value=sdk)
    monkeypatch.setattr("app.integrations.stripe.client.stripe.StripeClient", constructor)
    config = env.config.model_copy(update={"stripe_secret_key": SecretStr("sk_test_contract")})
    result = StripeClient(config).create_checkout(purchase)
    assert result.id == "cs_contract"
    params = create.call_args.kwargs["params"]
    assert params["line_items"][0]["price_data"]["unit_amount"] == 2000
    assert params["line_items"][0]["quantity"] == 1
    assert params["metadata"] == {"purchase_public_id": purchase.public_id}
    assert purchase.public_id in params["success_url"]
    assert create.call_args.kwargs["options"]["idempotency_key"] == f"checkout/{purchase.public_id}"


def test_resend_http_adapter_and_failure_messages(env, monkeypatch):
    config = env.config.model_copy(update={"resend_api_key": SecretStr("test-resend-key")})
    captured = {}

    def post(url, **kwargs):
        captured.update(kwargs)
        assert url == "https://api.resend.com/emails"
        return httpx.Response(200, json={"id": "mail-id"}, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.integrations.email.client.httpx.post", post)
    payload = {"from": "orders@example.com", "to": ["buyer@example.com"], "text": "Order"}
    assert ResendClient(config).send(payload, "delivery/order") == "mail-id"
    assert captured["headers"]["Idempotency-Key"] == "delivery/order"
    assert captured["json"] == payload

    def fail(*args, **kwargs):
        raise httpx.ReadTimeout("sensitive provider message")

    monkeypatch.setattr("app.integrations.email.client.httpx.post", fail)
    with pytest.raises(IntegrationError, match="Resend did not confirm"):
        ResendClient(config).send(payload, "delivery/order")


def test_unconfigured_integrations_raise_useful_errors(env):
    with pytest.raises(ConfigurationError, match="RESEND_API_KEY"):
        ResendClient(env.config).send({}, "key")
    with pytest.raises(ConfigurationError, match="STRIPE_SECRET_KEY"):
        StripeClient(env.config).create_checkout(None)
    config = env.config.model_copy(update={"stripe_webhook_secret": SecretStr("")})
    with pytest.raises(ConfigurationError, match="STRIPE_WEBHOOK_SECRET"):
        StripeClient(config).verify_event(b"{}", "signature")
    config = env.config.model_copy(update={"google_sheets_credentials_json": SecretStr("invalid")})
    with pytest.raises(ConfigurationError, match="JSON is invalid"):
        GoogleSheetsClient(config).fetch_rows("sheet", "Leads")


def test_google_adapter_uses_readonly_scope_and_quoted_tab(env, monkeypatch):
    module = "app.integrations.google_sheets.client"
    credentials = MagicMock()
    monkeypatch.setattr(f"{module}.Credentials.from_service_account_info", credentials)
    monkeypatch.setattr(f"{module}.google_auth_httplib2.AuthorizedHttp", MagicMock())
    service = MagicMock()
    service.__enter__.return_value = service
    service.spreadsheets().values().get().execute.return_value = {
        "values": [
            ["external_id", "lead_date", "first_name", "phone"],
            ["id", "2026-09-11", "Test", "7875550100"],
        ],
    }
    monkeypatch.setattr(f"{module}.build", MagicMock(return_value=service))
    config = env.config.model_copy(update={"google_sheets_credentials_json": SecretStr("{}")})
    rows = GoogleSheetsClient(config).fetch_rows("sheet-id", "Provider's Leads")
    assert rows[0]["external_id"] == "id"
    assert credentials.call_args.kwargs["scopes"] == [
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]
    assert service.spreadsheets().values().get.call_args.kwargs["range"] == "'Provider''s Leads'"
