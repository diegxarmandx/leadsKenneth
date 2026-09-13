import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from app.api.routes import admin, health, inventory, purchases, stripe
from app.core.config import Settings
from app.core.exceptions import DomainError
from app.core.logging import configure_logging
from app.core.runtime import Runtime
from app.db.session import make_engine, make_session_factory
from app.integrations.email.client import EmailClient, ResendClient
from app.integrations.google_sheets.client import GoogleSheetsClient, SheetClient
from app.integrations.stripe.client import CheckoutClient, StripeClient
from app.jobs.scheduler import SyncScheduler

logger = logging.getLogger(__name__)


def create_app(
    config: Settings | None = None,
    *,
    sheets: SheetClient | None = None,
    checkout: CheckoutClient | None = None,
    email: EmailClient | None = None,
) -> FastAPI:
    config = config or Settings()
    engine = make_engine(config.database_url)
    runtime = Runtime(
        config,
        make_session_factory(engine),
        sheets or GoogleSheetsClient(config),
        checkout or StripeClient(config),
        email or ResendClient(config),
    )
    scheduler = SyncScheduler(runtime)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        scheduler.start()
        try:
            yield
        finally:
            await run_in_threadpool(scheduler.stop)
            engine.dispose()

    app = FastAPI(title="LeadsPR API", version="0.1.0", lifespan=lifespan)
    app.state.runtime = runtime
    app.state.scheduler = scheduler
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[config.frontend_url],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "PUT"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(DomainError)
    async def domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"error": {"code": exc.code, "message": str(exc)}}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"location": list(item["loc"]), "type": item["type"], "message": item["msg"]}
            for item in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Invalid request",
                    "details": details,
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={"error": {"code": "http_error", "message": str(exc.detail)}},
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            "Unhandled request failure",
            extra={"error_type": type(exc).__name__, "request_id": request_id},
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                }
            },
            headers={"Cache-Control": "no-store", "X-Request-ID": request_id},
        )

    for router in (health.router, inventory.router, purchases.router, stripe.router, admin.router):
        app.include_router(router, prefix="/api/v1")
    return app


app = create_app()
