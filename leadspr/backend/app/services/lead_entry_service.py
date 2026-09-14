import logging
from uuid import UUID

from filelock import FileLock, Timeout
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.exceptions import DomainError, SheetSyncError
from app.db.session import lock_path
from app.integrations.google_sheets.client import SheetClient
from app.integrations.google_sheets.parser import NormalizedLead
from app.models import Lead
from app.models.enums import SyncStatus
from app.schemas.admin import SyncRunResponse
from app.schemas.lead_entry import LeadEntryInput, LeadEntryResponse
from app.services.inventory_service import InventoryService
from app.services.lead_sync_service import LeadSyncService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class LeadEntryService:
    def __init__(self, factory: sessionmaker[Session], config: Settings, client: SheetClient):
        self.factory, self.config, self.client = factory, config, client

    def create(self, data: LeadEntryInput, request_id: UUID) -> LeadEntryResponse:
        # Stable across retries/restarts, independent of local database IDs and row positions.
        external_id = f"LEAD-{request_id.hex.upper()}"
        lead = NormalizedLead(
            **data.model_dump(),
            external_id=external_id,
            insurance_type="Life Insurance",
            source="Admin",
            language="es",
        )
        with self.factory() as session:
            settings = SettingsService(session, self.config).all()
            path = lock_path(session.get_bind(), "lead-entry")
        try:
            # Serialize the upstream identity check + append across local server processes.
            with FileLock(path, timeout=0):
                appended = self.client.append_lead(
                    settings["google_sheet_id"],
                    settings["google_sheet_tab"],
                    lead,
                )
                result = LeadEntryResponse(
                    external_id=external_id,
                    appended=appended,
                    status="sync_pending",
                )
                try:
                    run = LeadSyncService(self.factory, self.config, self.client).sync(manual=True)
                    result.sync_run = SyncRunResponse.model_validate(run)
                    with self.factory() as session:
                        imported = session.scalar(
                            select(Lead).where(Lead.external_id == external_id)
                        )
                        if run.status == SyncStatus.SUCCESS and imported and imported.source_active:
                            result.status = "synced"
                            eligible = InventoryService(session, self.config).query()
                            result.available = (
                                session.scalar(eligible.where(Lead.external_id == external_id))
                                is not None
                            )
                except Exception as exc:
                    # The Sheet already owns this lead. Never append again to recover sync.
                    logger.exception(
                        "Lead was appended but automatic sync failed",
                        extra={"error_type": type(exc).__name__},
                    )
                return result
        except Timeout as exc:
            error = DomainError("Ya se está añadiendo un lead. Espera e intenta nuevamente.")
            error.status_code, error.code = 409, "lead_entry_busy"
            raise error from exc
        except (DomainError, SheetSyncError):
            raise
