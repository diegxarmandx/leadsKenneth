import json
import logging

from filelock import FileLock, Timeout
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, SheetSyncError
from app.db.session import lock_path, write_session
from app.integrations.google_sheets.client import SheetClient
from app.integrations.google_sheets.parser import ParseResult, parse_rows
from app.models import SyncRun
from app.models.enums import ActorType, SyncStatus
from app.repositories.lead_repository import LeadRepository
from app.repositories.sync_repository import SyncRepository
from app.services.audit_service import AuditService
from app.services.settings_service import SettingsService
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


class LeadSyncService:
    def __init__(
        self, factory: sessionmaker[Session], config: Settings, client: SheetClient
    ) -> None:
        self.factory, self.config, self.client = factory, config, client

    def sync(self, manual: bool = False) -> SyncRun:
        with write_session(self.factory) as session:
            run_id = SyncRepository(session).create().id
            if manual:
                AuditService(session).record(
                    "sync.invoked", "sync_run", run_id, actor=ActorType.ADMIN
                )
        try:
            with self.factory() as session:
                path = lock_path(session.get_bind(), "sync")
            with FileLock(path, timeout=0):
                with self.factory() as session:
                    settings = SettingsService(session, self.config).all()
                rows = self.client.fetch_rows(
                    settings["google_sheet_id"], settings["google_sheet_tab"]
                )
                with write_session(self.factory) as session:
                    SyncRepository(session).get(run_id).rows_received = len(rows)
                parsed = parse_rows(rows)
                with write_session(self.factory) as session:
                    run = SyncRepository(session).get(run_id)
                    self._apply(session, run, parsed)
                logger.info("Sheet sync completed", extra={"sync_run_id": run_id})
                return run
        except Exception as exc:
            if isinstance(exc, Timeout):
                message = "Another sync is running; retry later"
            elif isinstance(exc, (ConfigurationError, SheetSyncError)):
                message = str(exc)
            else:
                message = "Sync failed; no changes from this attempt were committed"
            with write_session(self.factory) as session:
                run = SyncRepository(session).get(run_id)
                run.status = SyncStatus.FAILED
                run.completed_at = utcnow()
                run.error_message = message
            logger.error(
                "Sheet sync failed", extra={"sync_run_id": run_id, "error_type": type(exc).__name__}
            )
            if isinstance(exc, ConfigurationError):
                raise ConfigurationError(f"{message} (sync run {run_id})") from exc
            raise SheetSyncError(f"{message} (sync run {run_id})") from exc

    @staticmethod
    def _apply(session: Session, run: SyncRun, parsed: ParseResult) -> None:
        repository = LeadRepository(session)
        existing = repository.by_external_id()
        now = utcnow()
        seen = set()
        for record in parsed.leads:
            seen.add(record.external_id)
            lead = existing.get(record.external_id)
            if lead is None:
                repository.add(**record.model_dump(), source_active=True, last_synced_at=now)
                run.leads_created += 1
            else:
                if not lead.source_active:
                    run.leads_reactivated += 1
                for name, value in record.model_dump().items():
                    setattr(lead, name, value)
                lead.source_active = True
                lead.last_synced_at = now
                lead.updated_at = now
                run.leads_updated += 1
        # An invalid row may hide an upstream ID. Reject it and suppress all deactivation
        # for this run instead of interpreting an incomplete valid subset as a full snapshot.
        if not parsed.rejected:
            for external_id, lead in existing.items():
                if external_id not in seen and lead.source_active:
                    lead.source_active = False
                    lead.updated_at = now
                    run.leads_deactivated += 1
        run.status = SyncStatus.FAILED if parsed.rejected else SyncStatus.SUCCESS
        run.completed_at = now
        if parsed.rejected or parsed.warnings:
            run.error_message = json.dumps(
                {
                    "rejected": parsed.rejected,
                    "warnings": parsed.warnings,
                    "deactivation_skipped": bool(parsed.rejected),
                }
            )
