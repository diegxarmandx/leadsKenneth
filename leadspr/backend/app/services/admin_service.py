from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import DomainError, NotFoundError
from app.models import Lead
from app.repositories.admin_repository import AdminRepository
from app.repositories.purchase_repository import PurchaseRepository
from app.schemas.admin import AdminLeadResponse, AdminPurchaseResponse
from app.services.inventory_service import InventoryService
from app.services.pricing_service import PricingService


class AdminService:
    def __init__(self, session: Session, config: Settings) -> None:
        self.session, self.config = session, config
        self.repository = AdminRepository(session)

    def leads(self, **filters) -> dict:
        minimum, maximum = filters["min_age_days"], filters["max_age_days"]
        if minimum is not None and maximum is not None and minimum > maximum:
            raise DomainError("min_age_days cannot exceed max_age_days")
        inventory = InventoryService(self.session, self.config)
        total, rows = self.repository.leads(rules=inventory.rules, today=inventory.today, **filters)
        items = []
        for lead, excluded_until in rows:
            rule = PricingService.applicable_rule(lead.lead_date, inventory.today, inventory.rules)
            values = {column.name: getattr(lead, column.name) for column in Lead.__table__.columns}
            items.append(
                AdminLeadResponse(
                    **values,
                    age_days=PricingService.age_days(lead.lead_date, inventory.today),
                    current_price_cents=rule.price_cents if rule else None,
                    currently_excluded=bool(excluded_until and excluded_until > inventory.now),
                    excluded_until=excluded_until,
                )
            )
        return {
            "total": total,
            "offset": filters["offset"],
            "limit": filters["limit"],
            "items": items,
        }

    def purchases(self, **filters) -> dict:
        start, end = filters["created_from"], filters["created_to"]
        if start and end and start >= end:
            raise DomainError("created_from must be before created_to")
        total, rows = self.repository.purchases(**filters)
        return {
            "total": total,
            "offset": filters["offset"],
            "limit": filters["limit"],
            "items": [AdminPurchaseResponse.model_validate(row) for row in rows],
        }

    def purchase(self, public_id: str) -> dict:
        purchase = PurchaseRepository(self.session).by_public_id(public_id, with_leads=True)
        if purchase is None:
            raise NotFoundError("Order not found")
        result = AdminPurchaseResponse.model_validate(purchase).model_dump()
        result["leads"] = [
            {
                "lead": {
                    column.name: getattr(item.lead, column.name)
                    for column in Lead.__table__.columns
                },
                "pricing_rule_id": item.pricing_rule_id,
                "price_paid_cents": item.price_paid_cents,
                "purchased_at": item.purchased_at,
                "excluded_until": item.excluded_until,
            }
            for item in purchase.purchase_leads
        ]
        return result
