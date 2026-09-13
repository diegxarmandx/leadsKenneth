from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.exceptions import ConfigurationError, SheetSyncError
from app.integrations.google_sheets.client import GoogleSheetsClient
from app.integrations.google_sheets.parser import parse_rows, values_to_rows
from app.models import Lead, PurchaseLead, SyncRun
from app.models.enums import SyncStatus
from app.services.lead_sync_service import LeadSyncService
from tests.conftest import exclusion


def row(env, **values):
    return {
        "external_id": "upstream-1",
        "lead_date": env.today.isoformat(),
        "first_name": "Sheet",
        "phone": "7875550101",
    } | values


def test_sync_create_update_deactivate_reactivate(env):
    env.sheets.rows = [row(env)]
    first = env.runtime.sync().sync()
    assert first.leads_created == 1 and first.rows_received == 1
    env.sheets.rows = [row(env, first_name="Updated")]
    assert env.runtime.sync().sync().leads_updated == 1
    with env.factory() as session:
        lead = session.scalar(select(Lead))
        assert lead.first_name == "Updated" and lead.insurance_type == "Life Insurance"
        assert lead.last_synced_at.tzinfo is not None
    env.sheets.rows = []
    assert env.runtime.sync().sync().leads_deactivated == 1
    assert env.runtime.sync().sync().leads_deactivated == 0
    env.sheets.rows = [row(env, insurance_type=" ")]
    assert env.runtime.sync().sync().leads_reactivated == 1
    with env.factory() as session:
        assert session.scalar(select(Lead)).source_active
        assert session.scalar(select(func.count()).select_from(SyncRun)) == 5


def test_sync_preserves_purchase_history(env, add_lead):
    lead_id = add_lead(external_id="upstream-1")
    exclusion(env, lead_id, env.now + timedelta(days=20))
    env.runtime.sync().sync()
    with env.factory() as session:
        assert not session.get(Lead, lead_id).source_active
        assert session.scalar(select(PurchaseLead)).lead_id == lead_id


def test_bad_required_row_recorded_and_deactivation_suppressed(env, add_lead):
    lead_id = add_lead()
    env.sheets.rows = [row(env, external_id=None), row(env, external_id="good")]
    run = env.runtime.sync().sync()
    assert run.status == SyncStatus.FAILED and run.leads_created == 1
    assert '"deactivation_skipped": true' in run.error_message
    assert "787555" not in run.error_message
    with env.factory() as session:
        assert session.get(Lead, lead_id).source_active


def test_optional_email_does_not_abort(env):
    env.sheets.rows = [row(env, email="broken-email")]
    run = env.runtime.sync().sync()
    assert run.status == SyncStatus.SUCCESS and run.leads_created == 1
    assert "invalid_optional_value" in run.error_message
    with env.factory() as session:
        assert session.scalar(select(Lead)).email is None


def test_duplicate_identifier_aborts_snapshot(env, add_lead):
    lead_id = add_lead()
    env.sheets.rows = [row(env), row(env)]
    with pytest.raises(SheetSyncError, match="Duplicate"):
        env.runtime.sync().sync()
    with env.factory() as session:
        assert session.scalar(select(func.count()).select_from(Lead)) == 1
        assert session.get(Lead, lead_id).source_active
        assert session.scalar(select(SyncRun)).status == SyncStatus.FAILED


def test_missing_credentials_records_failed_attempt(env):
    service = LeadSyncService(env.factory, env.config, GoogleSheetsClient(env.config))
    with pytest.raises(ConfigurationError, match="GOOGLE_SHEETS_CREDENTIALS_JSON"):
        service.sync(manual=True)
    with env.factory() as session:
        assert session.scalar(select(SyncRun)).status == SyncStatus.FAILED


@pytest.mark.parametrize(
    "values",
    [[], [["name", "phone"]], [["external_id", "lead_date", "first_name", "phone", "phone"]]],
)
def test_invalid_headers_are_not_empty_snapshots(values):
    with pytest.raises(SheetSyncError):
        values_to_rows(values)


def test_blank_rows_preserve_sheet_row_numbers(env):
    headers = ["external_id", "lead_date", "first_name", "phone"]
    rows = values_to_rows([headers, [], ["id", "not-a-date", "Name", "7875550100"]])
    assert parse_rows(rows).rejected[0]["row"] == 3


def test_failed_write_rolls_back_all_lead_changes(env, add_lead, monkeypatch):
    lead_id = add_lead()
    original = LeadSyncService._apply

    def fail(session, run, parsed):
        original(session, run, parsed)
        session.flush()
        raise RuntimeError("simulated failure with sensitive content")

    monkeypatch.setattr(LeadSyncService, "_apply", staticmethod(fail))
    env.sheets.rows = [row(env)]
    with pytest.raises(SheetSyncError):
        env.runtime.sync().sync()
    with env.factory() as session:
        assert session.get(Lead, lead_id).source_active
        assert session.scalar(select(func.count()).select_from(Lead)) == 1
        run = session.scalar(select(SyncRun))
        assert run.leads_created == 0 and "sensitive" not in run.error_message
