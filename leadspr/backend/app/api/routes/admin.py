from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Query
from pydantic import AwareDatetime

from app.api.dependencies.auth import require_admin
from app.api.dependencies.runtime import RuntimeDep, SessionDep, WriteSessionDep
from app.models import PricingRule, SyncRun
from app.models.enums import PurchaseStatus
from app.repositories.sync_repository import SyncRepository
from app.schemas.admin import SyncRunResponse
from app.schemas.lead_entry import LeadEntryInput, LeadEntryResponse
from app.schemas.pricing import (
    PricingRuleInput,
    PricingRulePatch,
    PricingRuleResponse,
    PricingRuleUpdate,
)
from app.services.admin_service import AdminService
from app.services.lead_entry_service import LeadEntryService
from app.services.pricing_service import PricingService
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=200)]


@router.get("/dashboard")
def dashboard(session: SessionDep, runtime: RuntimeDep) -> dict:
    return AdminService(session, runtime.config).dashboard()


@router.get("/leads")
def leads(
    session: SessionDep,
    runtime: RuntimeDep,
    offset: Offset = 0,
    limit: Limit = 50,
    external_id: str | None = None,
    municipality: str | None = None,
    source_active: bool | None = None,
    price_cents: Annotated[int | None, Query(gt=0)] = None,
    min_age_days: Annotated[int | None, Query(ge=0)] = None,
    max_age_days: Annotated[int | None, Query(ge=0)] = None,
) -> dict:
    return AdminService(session, runtime.config).leads(
        offset=offset,
        limit=limit,
        external_id=external_id,
        municipality=municipality,
        source_active=source_active,
        price_cents=price_cents,
        min_age_days=min_age_days,
        max_age_days=max_age_days,
    )


@router.post("/leads", response_model=LeadEntryResponse, status_code=201)
def create_lead(
    data: LeadEntryInput,
    runtime: RuntimeDep,
    idempotency_key: Annotated[UUID, Header()],
) -> LeadEntryResponse:
    return LeadEntryService(runtime.sessions, runtime.config, runtime.sheets).create(
        data, idempotency_key
    )


@router.get("/pricing-rules", response_model=list[PricingRuleResponse])
def pricing_rules(session: SessionDep) -> list[PricingRule]:
    return PricingService(session).list()


@router.post("/pricing-rules", response_model=PricingRuleResponse, status_code=201)
def create_rule(data: PricingRuleInput, session: WriteSessionDep) -> PricingRule:
    return PricingService(session).create(data)


@router.patch("/pricing-rules/{rule_id}", response_model=PricingRuleResponse)
def patch_rule(rule_id: int, data: PricingRulePatch, session: WriteSessionDep) -> PricingRule:
    return PricingService(session).update(rule_id, data)


@router.put("/pricing-rules", response_model=list[PricingRuleResponse])
def replace_rules(
    data: Annotated[list[PricingRuleUpdate], Body(min_length=1)], session: WriteSessionDep
) -> list[PricingRule]:
    return PricingService(session).update_batch(data)


@router.post("/sync", response_model=SyncRunResponse)
def sync(runtime: RuntimeDep) -> SyncRun:
    return runtime.sync().sync(manual=True)


@router.get("/sync-runs", response_model=list[SyncRunResponse])
def sync_runs(session: SessionDep, offset: Offset = 0, limit: Limit = 50) -> list[SyncRun]:
    return SyncRepository(session).list(offset, limit)


@router.get("/purchases")
def purchases(
    session: SessionDep,
    runtime: RuntimeDep,
    offset: Offset = 0,
    limit: Limit = 50,
    status: PurchaseStatus | None = None,
    buyer_email: str | None = None,
    public_id: str | None = None,
    created_from: AwareDatetime | None = None,
    created_to: AwareDatetime | None = None,
) -> dict:
    return AdminService(session, runtime.config).purchases(
        offset=offset,
        limit=limit,
        status=status,
        buyer_email=buyer_email,
        public_id=public_id,
        created_from=created_from,
        created_to=created_to,
    )


@router.get("/purchases/{public_id}")
def purchase(public_id: str, session: SessionDep, runtime: RuntimeDep) -> dict:
    return AdminService(session, runtime.config).purchase(public_id)


@router.post("/purchases/{public_id}/resend-email")
def resend(
    public_id: str,
    runtime: RuntimeDep,
    idempotency_key: Annotated[
        str, Header(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    ],
) -> dict:
    return {"sent": runtime.email().deliver(public_id, resend_key=idempotency_key)}


@router.get("/settings")
def settings(session: SessionDep, runtime: RuntimeDep) -> dict:
    return SettingsService(session, runtime.config).all()


@router.patch("/settings")
def patch_settings(data: dict[str, str], session: WriteSessionDep, runtime: RuntimeDep) -> dict:
    return SettingsService(session, runtime.config).update(data)
