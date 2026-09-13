from fastapi import APIRouter
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies.runtime import SessionDep
from app.core.exceptions import ConfigurationError
from app.models import Lead

router = APIRouter(tags=["health"])


@router.get("/health")
def health(session: SessionDep) -> dict:
    try:
        session.execute(text("SELECT 1"))
        session.execute(select(Lead.id).limit(0))
    except SQLAlchemyError as exc:
        raise ConfigurationError(
            "Database unavailable or migrations have not been applied"
        ) from exc
    return {"status": "ok", "database": "ok"}
