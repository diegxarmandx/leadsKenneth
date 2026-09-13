from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, **values) -> AuditLog:
        entry = AuditLog(**values)
        self.session.add(entry)
        return entry

    def has_action(self, action: str, entity_id: str, new_values: str) -> bool:
        return (
            self.session.scalar(
                select(AuditLog.id)
                .where(
                    AuditLog.action == action,
                    AuditLog.entity_id == entity_id,
                    AuditLog.new_values == new_values,
                )
                .limit(1)
            )
            is not None
        )
