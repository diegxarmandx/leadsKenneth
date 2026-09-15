import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from filelock import FileLock, Timeout

from app.core.runtime import Runtime
from app.db.session import lock_path
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class SyncScheduler:
    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime
        self.scheduler = BackgroundScheduler(timezone=runtime.config.app_timezone)
        with runtime.sessions() as session:
            self.lock = FileLock(lock_path(session.get_bind(), "scheduler"), thread_local=False)
        self.schedule: tuple[str, str] | None = None
        self.owner = False

    def start(self) -> None:
        if not self.runtime.config.scheduler_enabled:
            return
        try:
            self.lock.acquire(timeout=0)
        except Timeout:
            logger.info("Scheduler already owned by another local process")
            return
        self.owner = True
        try:
            self.refresh()
            self.scheduler.add_job(
                self.runtime.reconciliation().recover_pending,
                "interval",
                seconds=60,
                id="recover-checkout-orders",
                max_instances=1,
                coalesce=True,
            )
            self.scheduler.add_job(
                self.refresh,
                "interval",
                seconds=60,
                id="refresh-sync-schedule",
                max_instances=1,
                coalesce=True,
            )
            self.scheduler.start()
        except Exception:
            self.lock.release()
            self.owner = False
            raise

    def refresh(self) -> None:
        try:
            with self.runtime.sessions() as session:
                settings = SettingsService(session, self.runtime.config).all()
            schedule = (settings["daily_sync_time"], settings["timezone"])
            if schedule != self.schedule:
                hour, minute = map(int, schedule[0].split(":"))
                self.scheduler.add_job(
                    self.run,
                    CronTrigger(hour=hour, minute=minute, timezone=schedule[1]),
                    id="daily-lead-sync",
                    replace_existing=True,
                    max_instances=1,
                    coalesce=True,
                    misfire_grace_time=3600,
                )
                self.schedule = schedule
        except Exception as exc:
            logger.error(
                "Cannot configure sync schedule; check database migrations and settings",
                extra={"error_type": type(exc).__name__},
            )

    def run(self) -> None:
        try:
            self.runtime.sync().sync()
        except Exception:
            # The service has already persisted and logged sanitized failure details.
            logger.error("Scheduled sync did not complete successfully")

    def stop(self) -> None:
        if self.owner:
            try:
                if self.scheduler.running:
                    self.scheduler.shutdown(wait=True)
            finally:
                self.lock.release()
                self.owner = False
