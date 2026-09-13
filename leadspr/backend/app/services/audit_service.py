import json

from sqlalchemy.orm import Session

from app.models.enums import ActorType
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, session: Session) -> None:
        self.repository = AuditRepository(session)

    def record(
        self,
        action: str,
        entity_type: str | None = None,
        entity_id: str | int | None = None,
        *,
        actor: ActorType = ActorType.SYSTEM,
        old: dict | None = None,
        new: dict | None = None,
    ) -> None:
        self.repository.add(
            actor_type=actor,
            actor_identifier="admin-token" if actor == ActorType.ADMIN else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            old_values=json.dumps(old, default=str) if old is not None else None,
            new_values=json.dumps(new, default=str) if new is not None else None,
        )
