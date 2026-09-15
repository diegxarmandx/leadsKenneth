from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from alembic.config import Config
from filelock import FileLock
from sqlalchemy import inspect, text

from alembic import command
from app.db.session import lock_path, make_engine, write_session
from app.jobs.scheduler import SyncScheduler
from app.services.settings_service import SettingsService


def test_migration_roundtrip_creates_exact_domain_schema(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(root / "alembic.ini"))
    command.upgrade(config, "head")
    engine = make_engine(url)
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {
        "alembic_version",
        "leads",
        "pricing_rules",
        "purchases",
        "purchase_leads",
        "app_settings",
        "sync_runs",
        "audit_logs",
    }
    assert not {"current_price", "lead_age", "pricing_category", "sold"} & {
        column["name"] for column in inspector.get_columns("leads")
    }
    assert len(inspector.get_foreign_keys("purchase_leads")) == 3
    with engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1
    command.check(config)
    engine.dispose()
    command.downgrade(config, "base")
    engine = make_engine(url)
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    engine.dispose()
    command.upgrade(config, "head")


def test_scheduler_lock_refresh_and_cross_thread_shutdown(env):
    env.config.scheduler_enabled = True
    first = SyncScheduler(env.runtime)
    second = SyncScheduler(env.runtime)
    first.start()
    try:
        second.start()
        assert first.owner and not second.owner
        assert first.scheduler.get_job("daily-lead-sync") is not None
        assert first.scheduler.get_job("recover-checkout-orders") is not None
        with write_session(env.factory) as session:
            SettingsService(session, env.config).update(
                {"daily_sync_time": "04:15", "timezone": "UTC"}
            )
        first.refresh()
        assert first.schedule == ("04:15", "UTC")
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(first.stop).result(timeout=10)
        second.start()
        assert second.owner
    finally:
        first.stop()
        second.stop()


def test_overlapping_sync_attempt_is_recorded_without_mutation(env):
    import pytest
    from sqlalchemy import select

    from app.core.exceptions import SheetSyncError
    from app.models import SyncRun
    from app.models.enums import SyncStatus

    with env.factory() as session:
        path = lock_path(session.get_bind(), "sync")
    with FileLock(path):
        with pytest.raises(SheetSyncError, match="Another sync"):
            env.runtime.sync().sync()
    with env.factory() as session:
        assert session.scalar(select(SyncRun)).status == SyncStatus.FAILED
