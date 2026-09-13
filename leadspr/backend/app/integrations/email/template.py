from html import escape

from app.models import Purchase

DELIVERY_FIELDS = (
    ("first_name", "First name"),
    ("last_name", "Last name"),
    ("phone", "Phone"),
    ("email", "Email"),
    ("municipality", "Municipality"),
    ("lead_date", "Lead date"),
    ("source", "Source"),
    ("campaign", "Campaign"),
    ("language", "Language"),
    ("notes", "Notes"),
)


def delivery_payload(purchase: Purchase, sender: str, company: str) -> dict:
    dollars, cents = divmod(purchase.total_amount_cents, 100)
    heading = (
        f"{company} — {purchase.public_id}\n"
        f"{purchase.requested_quantity} leads · USD ${dollars:,}.{cents:02d}"
    )
    text_blocks = [heading]
    html_blocks = [f"<h1>{escape(company)}</h1><p>{escape(heading)}</p>"]
    for number, allocation in enumerate(sorted(purchase.purchase_leads, key=lambda p: p.id), 1):
        fields = [
            (label, str(getattr(allocation.lead, key)))
            for key, label in DELIVERY_FIELDS
            if getattr(allocation.lead, key) is not None
        ]
        text_blocks.append(f"Lead {number}\n" + "\n".join(f"{k}: {v}" for k, v in fields))
        html_blocks.append(
            f"<h2>Lead {number}</h2><dl>"
            + "".join(
                f"<dt>{escape(label)}</dt><dd>{escape(value)}</dd>" for label, value in fields
            )
            + "</dl>"
        )
    return {
        "from": sender,
        "to": [purchase.buyer_email],
        "subject": f"Your LeadsPR order {purchase.public_id}",
        "text": "\n\n".join(text_blocks),
        "html": "".join(html_blocks),
    }
