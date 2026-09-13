from typing import Annotated

from fastapi import APIRouter, Header, Request
from starlette.concurrency import run_in_threadpool

from app.api.dependencies.runtime import RuntimeDep
from app.core.exceptions import DomainError

router = APIRouter(prefix="/webhooks", tags=["stripe"])


@router.post("/stripe")
async def webhook(
    request: Request,
    runtime: RuntimeDep,
    stripe_signature: Annotated[str, Header()] = "",
) -> dict:
    payload = bytearray()
    async for chunk in request.stream():
        payload.extend(chunk)
        if len(payload) > 1_000_000:
            raise DomainError("Webhook payload exceeds 1 MB")
    return await run_in_threadpool(runtime.webhooks().process, bytes(payload), stripe_signature)
