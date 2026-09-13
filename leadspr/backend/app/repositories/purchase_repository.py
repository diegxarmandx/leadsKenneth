from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Purchase, PurchaseLead


class PurchaseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def by_public_id(self, public_id: str, with_leads: bool = False) -> Purchase | None:
        query = select(Purchase).where(Purchase.public_id == public_id)
        if with_leads:
            query = query.options(
                selectinload(Purchase.purchase_leads).selectinload(PurchaseLead.lead)
            )
        return self.session.scalar(query)

    def add(self, **values) -> Purchase:
        purchase = Purchase(**values)
        self.session.add(purchase)
        self.session.flush()
        return purchase

    def add_allocation(self, **values) -> None:
        self.session.add(PurchaseLead(**values))
