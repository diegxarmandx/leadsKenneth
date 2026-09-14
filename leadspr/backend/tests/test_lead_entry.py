from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.exceptions import SheetSyncError
from app.integrations.google_sheets.client import GoogleSheetsClient, SheetWriteError
from app.integrations.google_sheets.parser import NormalizedLead
from app.models import Lead
from app.schemas.lead_entry import LeadEntryInput
from app.services.lead_entry_service import LeadEntryService
from app.services.lead_sync_service import LeadSyncService


def payload(env, **changes):
    return (
        dict(
            first_name="Prueba",
            last_name="Demo",
            phone="+1 (787) 555-0100",
            email="test@example.com",
            municipality="Salinas",
            lead_date=env.today.isoformat(),
        )
        | changes
    )


def submit(env, data=None, key=None):
    return env.client.post(
        "/api/v1/admin/leads",
        json=data or payload(env),
        headers=env.admin | {"Idempotency-Key": str(key or uuid4())},
    )


def test_admin_auth_and_idempotency_key_required(env):
    assert env.client.post("/api/v1/admin/leads", json=payload(env)).status_code == 401
    assert (
        env.client.post("/api/v1/admin/leads", json=payload(env), headers=env.admin).status_code
        == 422
    )
    assert not env.sheets.append_calls


def test_append_then_existing_sync_and_restart_are_idempotent(env, monkeypatch):
    calls = []
    original = LeadSyncService.sync

    def track(self, manual=False):
        assert len(env.sheets.rows) == 1  # Upstream row exists before sync is invoked.
        calls.append(manual)
        return original(self, manual)

    monkeypatch.setattr(LeadSyncService, "sync", track)
    key = uuid4()
    response = submit(env, key=key)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "synced" and data["available"]
    assert data["external_id"] == f"LEAD-{key.hex.upper()}"
    assert data["sync_run"]["leads_created"] == 1
    assert env.sheets.append_calls[0][:2] == ("test-sheet", "Leads")
    replay = submit(env, key=key).json()
    assert not replay["appended"] and replay["external_id"] == data["external_id"]
    # A new service instance has no in-memory identity state to lose on restart.
    restarted = LeadEntryService(env.factory, env.config, env.sheets)
    assert not restarted.create(LeadEntryInput(**payload(env)), key).appended
    env.runtime.sync().sync(manual=True)
    assert len(env.sheets.append_calls) == 1 and all(calls)
    with env.factory() as session:
        assert session.scalar(select(func.count()).select_from(Lead)) == 1
        lead = session.scalar(select(Lead))
        assert lead.insurance_type == "Life Insurance" and lead.source == "Admin"
    assert submit(env).json()["external_id"] != data["external_id"]


@pytest.mark.parametrize(
    "changes",
    [
        {"first_name": "  "},
        {"phone": "abc"},
        {"phone": "123"},
        {"phone": 1234567890},
        {"email": "invalid"},
        {"municipality": "Atlantis"},
        {"lead_date": "2026-02-30"},
        {"lead_date": 0},
        {"insurance_type": "Auto"},
        {"external_id": "injected"},
    ],
)
def test_invalid_input_never_writes(env, changes):
    assert submit(env, payload(env, **changes)).status_code == 422
    assert not env.sheets.append_calls


def test_partial_sync_failure_does_not_reappend(env):
    env.sheets.error = SheetSyncError("sensitive details")
    key = uuid4()
    response = submit(env, key=key)
    assert response.status_code == 201
    assert response.json()["status"] == "sync_pending"
    assert response.json()["sheet_written"]
    assert "sensitive" not in response.text
    assert submit(env, key=key).json()["status"] == "sync_pending"
    assert len(env.sheets.append_calls) == 1
    env.sheets.error = None
    assert env.runtime.sync().sync(manual=True).leads_created == 1
    assert submit(env, key=key).json()["status"] == "synced"
    assert len(env.sheets.rows) == 1


def test_write_failure_never_syncs_or_inserts(env, monkeypatch):
    env.sheets.append_error = SheetWriteError("No se pudo conectar con Google Sheets.")
    sync = MagicMock()
    monkeypatch.setattr(LeadSyncService, "sync", sync)
    response = submit(env)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "sheet_write_failed"
    sync.assert_not_called()
    with env.factory() as session:
        assert session.scalar(select(func.count()).select_from(Lead)) == 0


def test_all_municipalities_available_even_with_no_inventory(env):
    assert env.client.get("/api/v1/inventory/municipalities").json()["municipalities"] == []
    places = env.client.get("/api/v1/inventory/municipalities?scope=all").json()["municipalities"]
    assert len(places) == 78 and "Salinas" in places and "Bayamón" in places


def test_append_adapter_maps_actual_headers_raw_values_and_replays(env, monkeypatch):
    service = MagicMock()
    service.__enter__.return_value = service
    values_api = service.spreadsheets().values()
    headers = [
        "id",
        "external_id",
        "lead_date",
        "first_name",
        "last_name",
        "phone",
        "email",
        "municipality",
        "insurance_type",
        "source",
        "campaign",
        "language",
    ]
    values_api.get().execute.return_value = {"values": [headers]}
    values_api.append().execute.return_value = {"updates": {"updatedRows": 1}}
    adapter = GoogleSheetsClient(env.config)
    monkeypatch.setattr(adapter, "_service", MagicMock(return_value=service))
    lead = NormalizedLead(
        **payload(env, phone="007875550100"),
        external_id="LEAD-UNIQUE",
        source="Admin",
        language="es",
    )
    assert adapter.append_lead("sheet", "Client's Leads", lead)
    args = values_api.append.call_args.kwargs
    expected = [
        "",
        "LEAD-UNIQUE",
        env.today.isoformat(),
        "Prueba",
        "Demo",
        "007875550100",
        "test@example.com",
        "Salinas",
        "Life Insurance",
        "Admin",
        "",
        "es",
    ]
    assert args["body"]["values"] == [expected]
    assert args["range"] == "'Client''s Leads'"
    assert args["valueInputOption"] == "RAW" and args["insertDataOption"] == "INSERT_ROWS"
    values_api.append().execute.assert_called_with(num_retries=0)
    values_api.get().execute.return_value = {"values": [headers, expected]}
    values_api.append.reset_mock()
    assert not adapter.append_lead("sheet", "Client's Leads", lead)
    values_api.append.assert_not_called()
    values_api.get().execute.return_value = {"values": [headers[::-1]]}
    assert adapter.append_lead("sheet", "Leads", lead)
    assert values_api.append.call_args.kwargs["body"]["values"] == [expected[::-1]]


def test_provider_failure_is_sanitized(env, monkeypatch):
    adapter = GoogleSheetsClient(env.config)
    monkeypatch.setattr(adapter, "_service", MagicMock(side_effect=RuntimeError("PRIVATE KEY")))
    with pytest.raises(SheetWriteError) as failure:
        adapter.append_lead("sheet", "Leads", NormalizedLead(**payload(env), external_id="LEAD-X"))
    assert "PRIVATE KEY" not in str(failure.value)


def test_invalid_existing_row_keeps_append_as_partial_success(env):
    env.sheets.rows = [
        {
            "external_id": "bad-date",
            "first_name": "Old",
            "phone": "7875550100",
            "lead_date": "not-a-date",
        }
    ]
    response = submit(env)
    assert response.status_code == 201
    assert response.json()["status"] == "sync_pending"
    assert response.json()["sync_run"]["status"] == "FAILED"
    assert response.json()["sync_run"]["leads_created"] == 1
    assert len(env.sheets.append_calls) == 1


def test_selected_date_is_preserved_and_future_lead_is_not_advertised_as_available(env):
    from datetime import timedelta

    chosen = (env.today + timedelta(days=10)).isoformat()
    result = submit(env, payload(env, lead_date=chosen)).json()
    assert result["status"] == "synced" and not result["available"]
    assert env.sheets.rows[0]["lead_date"] == chosen


def test_same_key_conflicting_data_or_bad_schema_never_appends(env, monkeypatch):
    from app.integrations.google_sheets.client import SheetIdentityConflict

    service = MagicMock()
    service.__enter__.return_value = service
    values_api = service.spreadsheets().values()
    lead = NormalizedLead(**payload(env), external_id="LEAD-SAME")
    headers = [
        "external_id",
        "lead_date",
        "first_name",
        "phone",
        "municipality",
        "last_name",
        "email",
    ]
    existing = [
        "LEAD-SAME",
        env.today.isoformat(),
        "Different",
        lead.phone,
        "Salinas",
        "Demo",
        "test@example.com",
    ]
    values_api.get().execute.return_value = {"values": [headers, existing]}
    adapter = GoogleSheetsClient(env.config)
    monkeypatch.setattr(adapter, "_service", MagicMock(return_value=service))
    with pytest.raises(SheetIdentityConflict):
        adapter.append_lead("sheet", "Leads", lead)
    values_api.append.assert_not_called()
    values_api.get().execute.return_value = {"values": [["external_id", "phone"]]}
    with pytest.raises(SheetWriteError):
        adapter.append_lead("sheet", "Leads", lead)
    values_api.append.assert_not_called()


def test_entry_lock_prevents_overlapping_append(env):
    from filelock import FileLock

    from app.db.session import lock_path

    with env.factory() as session:
        path = lock_path(session.get_bind(), "lead-entry")
    with FileLock(path):
        response = submit(env)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "lead_entry_busy"
    assert not env.sheets.append_calls
