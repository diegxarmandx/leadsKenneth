import base64
import re
from email.utils import formataddr, parseaddr
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import quote

from app.models import Purchase

ASSETS = Path(__file__).parent / "assets"
FSG_NAME = "FSG Seguros"
DELIVERY_FIELDS = (
    ("first_name", "Nombre"),
    ("last_name", "Apellido"),
    ("phone", "Teléfono"),
    ("email", "Correo electrónico"),
    ("municipality", "Municipio"),
    ("lead_date", "Fecha del lead"),
    ("source", "Origen"),
    ("campaign", "Campaña"),
    ("language", "Idioma"),
    ("notes", "Notas"),
)


def _field_html(key: str, value: str) -> str:
    content = escape(value).replace("\n", "<br>")
    href = ""
    if key == "phone" and re.fullmatch(r"\+?[\d\s().-]+", value):
        href = "tel:" + re.sub(r"[^\d+]", "", value)
    elif key == "email" and re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        # Encode query delimiters so a stored address cannot add mail headers.
        href = "mailto:" + quote(value, safe="@.+")
    if href:
        return (
            f'<a href="{escape(href, quote=True)}" '
            'style="color:#d7e9a0;text-decoration:underline;'
            f'display:inline-block;padding:10px 0;">{content}</a>'
        )
    return content


def delivery_payload(purchase: Purchase, sender: str, company: str) -> dict:
    # Existing installations still store the former marketplace name in settings.
    brand = FSG_NAME if company.strip() in {"LeadsPR", FSG_NAME} else company
    is_fsg = brand == FSG_NAME
    display_name, address = parseaddr(sender)
    if is_fsg and display_name == "LeadsPR":
        sender = formataddr((FSG_NAME, address))
    dollars, cents = divmod(purchase.total_amount_cents, 100)
    amount = f"USD ${dollars:,}.{cents:02d}"
    quantity = purchase.requested_quantity
    count = f"{quantity} {'lead' if quantity == 1 else 'leads'}"
    title = "Tu lead está listo" if quantity == 1 else "Tus leads están listos"
    greeting = f"Hola, {purchase.buyer_name}."
    introduction = "Gracias por tu compra. Aquí tienes los contactos de tu orden."
    privacy = (
        "Estos datos son para tu gestión profesional. Protege la información de tus contactos."
    )
    text_blocks = [
        f"{brand}\n{title}\n\n{greeting}\n{introduction}",
        f"Orden: {purchase.public_id}\nCantidad: {count}\nTotal pagado: {amount}",
    ]
    cards = []
    for number, allocation in enumerate(sorted(purchase.purchase_leads, key=lambda p: p.id), 1):
        lead = allocation.lead
        fields = [
            (key, label, str(getattr(lead, key)))
            for key, label in DELIVERY_FIELDS
            if getattr(lead, key) is not None and str(getattr(lead, key)).strip()
        ]
        name = " ".join(str(part) for part in (lead.first_name, lead.last_name) if part)
        text_blocks.append(
            f"Lead {number}\n" + "\n".join(f"{label}: {value}" for _, label, value in fields)
        )
        rows = "".join(
            '<tr><th scope="row" width="35%" valign="top" '
            'style="text-align:left;padding:12px 12px 12px 0;border-top:1px solid #36506e;'
            f'font-size:12px;font-weight:400;color:#c8d5e5;">{escape(label)}</th>'
            '<td valign="top" style="padding:12px 0;border-top:1px solid #36506e;'
            'font-size:14px;color:#ffffff;overflow-wrap:anywhere;word-break:break-word;">'
            f"{_field_html(key, value)}</td></tr>"
            for key, label, value in fields
            if key not in {"first_name", "last_name"}
        )
        cards.append(
            '<tr><td style="padding:0 0 16px;">'
            '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
            'bgcolor="#10233f" style="table-layout:fixed;border-radius:12px;color:#ffffff;">'
            '<tr><td style="padding:24px;">'
            '<p style="margin:0 0 8px;font-size:11px;letter-spacing:2px;color:#d7e9a0;">'
            f'CONTACTO {number:02d}</p><h2 style="margin:0 0 20px;font-size:24px;'
            'line-height:1.3;font-weight:700;overflow-wrap:anywhere;word-break:break-word;">'
            f'{escape(name)}</h2><table aria-label="Datos del contacto {number}" '
            'width="100%" cellspacing="0" cellpadding="0" '
            f'style="table-layout:fixed;line-height:1.5;">{rows}</table>'
            "</td></tr></table></td></tr>"
        )
    text_blocks.extend([privacy, brand])
    logo = (
        '<img src="cid:fsg-logo" alt="Financial Support Group Inc." width="144" height="144" '
        'style="display:block;width:144px;height:144px;border:0;margin:0 auto;">'
        if is_fsg
        else ""
    )
    html = Template((ASSETS / "delivery.html").read_text(encoding="utf-8")).substitute(
        brand=escape(brand),
        title=escape(title),
        greeting=escape(greeting),
        introduction=escape(introduction),
        order=escape(purchase.public_id),
        count=escape(count),
        amount=escape(amount),
        cards="".join(cards),
        logo=logo,
        privacy=escape(privacy),
    )
    payload = {
        "from": sender,
        "to": [purchase.buyer_email],
        "subject": f"{brand} · {title} · {purchase.public_id}",
        "text": "\n\n".join(text_blocks),
        "html": html,
    }
    if is_fsg:
        # CID works without a public frontend URL. Keep the original supplied logo.
        payload["attachments"] = [
            {
                "filename": "logo-fsg.jpg",
                "content": base64.b64encode((ASSETS / "logo-fsg.jpg").read_bytes()).decode("ascii"),
                "content_id": "fsg-logo",
                "content_type": "image/jpeg",
            }
        ]
    return payload
