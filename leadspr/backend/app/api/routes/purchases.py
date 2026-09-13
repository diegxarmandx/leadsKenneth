from fastapi import APIRouter

from app.api.dependencies.runtime import RuntimeDep
from app.schemas.purchase import CheckoutRequest, CheckoutResponse, PurchaseResponse

router = APIRouter(tags=["purchases"])


@router.get("/checkout/config")
def checkout_config(runtime: RuntimeDep) -> dict:
    return {"payment_mode": runtime.config.payment_mode}


@router.post("/checkout", response_model=CheckoutResponse, status_code=201)
def checkout(data: CheckoutRequest, runtime: RuntimeDep) -> CheckoutResponse:
    return runtime.purchases().create_checkout(data)


@router.get("/purchases/{public_id}", response_model=PurchaseResponse)
def purchase(public_id: str, runtime: RuntimeDep) -> PurchaseResponse:
    return runtime.purchases().get_public(public_id)
