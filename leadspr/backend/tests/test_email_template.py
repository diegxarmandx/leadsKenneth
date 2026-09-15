import base64
from datetime import date
from email.utils import parseaddr
from html.parser import HTMLParser

from app.integrations.email.template import ASSETS, delivery_payload
from app.models import Lead, Purchase, PurchaseLead


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def sample_purchase(**lead_values):
    lead = Lead(
        **{
            "first_name": "María",
            "last_name": "Rivera",
            "phone": "+1 (787) 555-0100",
            "email": "maria.rivera@example.com",
            "municipality": "Bayamón",
            "lead_date": date(2026, 9, 14),
            "source": "Formulario web",
            "campaign": "Protección familiar",
            "language": "Español",
            "notes": "Prefiere llamadas por la tarde.\nSolicitó orientación.",
        }
        | lead_values
    )
    return Purchase(
        public_id="ORD-DEMO20260914",
        buyer_name="Agente de demostración",
        buyer_email="preview@example.com",
        requested_quantity=1,
        total_amount_cents=1500,
        purchase_leads=[PurchaseLead(id=1, lead=lead)],
    )


def test_spanish_order_and_all_lead_data_are_preserved():
    purchase = sample_purchase()
    payload = delivery_payload(purchase, "LeadsPR <onboarding@resend.dev>", "LeadsPR")
    assert payload["subject"] == "FSG Seguros · Tu lead está listo · ORD-DEMO20260914"
    assert parseaddr(payload["from"])[1] == "onboarding@resend.dev"
    assert parseaddr(payload["from"])[0] == "FSG Seguros"
    assert payload["to"] == [purchase.buyer_email]
    for value in [
        "María",
        "Rivera",
        "+1 (787) 555-0100",
        "maria.rivera@example.com",
        "Bayamón",
        "2026-09-14",
        "Formulario web",
        "Protección familiar",
        "Español",
        "Prefiere llamadas por la tarde.",
        "Solicitó orientación.",
        "USD $15.00",
        "1 lead",
    ]:
        assert value in payload["html"]
        assert value in payload["text"]
    assert '<html lang="es">' in payload["html"]
    assert 'href="tel:+17875550100"' in payload["html"]
    assert 'href="mailto:maria.rivera@example.com"' in payload["html"]
    assert "First name" not in payload["html"]


def test_inline_logo_uses_original_bytes_and_matching_cid():
    payload = delivery_payload(sample_purchase(), "orders@example.com", "LeadsPR")
    (attachment,) = payload["attachments"]
    assert base64.b64decode(attachment["content"]) == (ASSETS / "logo-fsg.jpg").read_bytes()
    assert f'src="cid:{attachment["content_id"]}"' in payload["html"]
    assert attachment["content_type"] == "image/jpeg"
    assert "localhost" not in payload["html"]


def test_dynamic_fields_cannot_inject_html_or_mail_headers():
    malicious = '<script>alert("test")</script>'
    purchase = sample_purchase(
        first_name=malicious,
        phone='" onclick="alert(1)',
        email="person@example.com?subject=unsafe&bcc=other@example.com",
        notes=malicious,
    )
    purchase.buyer_name = malicious
    payload = delivery_payload(purchase, "orders@example.com", '<img src=x onerror="alert(1)">')
    elements = Elements(payload["html"]).elements
    assert not any(tag in {"script", "img"} for tag, _ in elements)
    assert not any(key.startswith("on") for _, attrs in elements for key in attrs)
    assert "&lt;script&gt;" in payload["html"]
    assert malicious in payload["text"]
    assert not any(attrs.get("href", "").startswith("tel:") for _, attrs in elements)
    assert not any(attrs.get("href", "").startswith("mailto:") for _, attrs in elements)


def test_email_link_query_delimiters_are_encoded():
    payload = delivery_payload(
        sample_purchase(email="person?subject=unsafe@example.com"), "orders@example.com", "LeadsPR"
    )
    links = [attrs["href"] for tag, attrs in Elements(payload["html"]).elements if tag == "a"]
    assert "mailto:person%3Fsubject%3Dunsafe@example.com" in links


def test_optional_fields_ordering_plural_and_custom_brand():
    purchase = sample_purchase(last_name=None, email=None, notes=None)
    purchase.purchase_leads.insert(
        0, PurchaseLead(id=2, lead=Lead(first_name="Segundo", phone="123"))
    )
    purchase.requested_quantity = 2
    purchase.total_amount_cents = 123456
    payload = delivery_payload(purchase, "Custom <orders@example.com>", "Mi agencia")
    assert payload["from"] == "Custom <orders@example.com>"
    assert "Mi agencia · Tus leads están listos" in payload["subject"]
    assert "attachments" not in payload
    assert "USD $1,234.56" in payload["html"]
    assert payload["html"].index("María") < payload["html"].index("Segundo")
    assert "Correo electrónico" not in payload["html"]
    assert "None" not in payload["html"]
