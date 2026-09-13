from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies.runtime import RuntimeDep, SessionDep
from app.schemas.purchase import InsuranceType
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/summary")
def summary(
    session: SessionDep,
    runtime: RuntimeDep,
    municipality: Annotated[str | None, Query(max_length=100)] = None,
    insurance_type: InsuranceType = "Life Insurance",
) -> dict:
    return InventoryService(session, runtime.config).summary(municipality, insurance_type)


@router.get("/municipalities")
def municipalities(
    session: SessionDep,
    runtime: RuntimeDep,
    insurance_type: InsuranceType = "Life Insurance",
) -> dict:
    return {
        "municipalities": InventoryService(session, runtime.config).municipalities(insurance_type)
    }
