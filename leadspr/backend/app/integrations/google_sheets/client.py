import json
import logging
from typing import Any, Protocol

import google_auth_httplib2
import httplib2
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, DomainError, SheetSyncError
from app.integrations.google_sheets.parser import NormalizedLead, clean_cell, values_to_rows

logger = logging.getLogger(__name__)


class SheetWriteError(DomainError):
    status_code = 502
    code = "sheet_write_failed"


class SheetIdentityConflict(DomainError):
    status_code = 409
    code = "lead_identity_conflict"


class SheetClient(Protocol):
    def fetch_rows(self, sheet_id: str, tab: str) -> list[dict[str, Any]]: ...

    def append_lead(self, sheet_id: str, tab: str, lead: NormalizedLead) -> bool: ...


def row_for_headers(headers: list[Any], lead: NormalizedLead) -> list[str]:
    # Use the same normalization/validation as import. Unknown columns (including id)
    # stay blank. Their positions never shift the known columns.
    values_to_rows([headers])
    names = [str(value).strip().lower() for value in headers]
    data = lead.model_dump(mode="json")
    for field in ("last_name", "email", "municipality"):
        if data[field] and field not in names:
            raise SheetWriteError("La hoja no contiene las columnas necesarias para este lead.")
    return [data.get(name) or "" for name in names]


class GoogleSheetsClient:
    def __init__(self, config: Settings) -> None:
        self.config = config

    def _service(self, sheet_id: str, tab: str, *, write: bool = False):
        secret = self.config.google_sheets_credentials_json.get_secret_value()
        if not secret or not sheet_id or not tab:
            raise ConfigurationError(
                "Configure GOOGLE_SHEETS_CREDENTIALS_JSON, GOOGLE_SHEET_ID, "
                "and GOOGLE_SHEET_TAB before synchronization"
            )
        scope = "spreadsheets" if write else "spreadsheets.readonly"
        try:
            credentials = Credentials.from_service_account_info(
                json.loads(secret),
                scopes=[f"https://www.googleapis.com/auth/{scope}"],
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise ConfigurationError("Google service account JSON is invalid") from exc
        http = google_auth_httplib2.AuthorizedHttp(credentials, http=httplib2.Http(timeout=30))
        return build("sheets", "v4", http=http, cache_discovery=False)

    def fetch_rows(self, sheet_id: str, tab: str) -> list[dict[str, Any]]:
        try:
            with self._service(sheet_id, tab) as service:
                escaped_tab = tab.replace("'", "''")
                result = (
                    service.spreadsheets()
                    .values()
                    .get(
                        spreadsheetId=sheet_id,
                        range=f"'{escaped_tab}'",
                        valueRenderOption="FORMATTED_VALUE",
                    )
                    .execute(num_retries=2)
                )
            return values_to_rows(result.get("values", []))
        except (ConfigurationError, SheetSyncError):
            raise
        except Exception as exc:
            raise SheetSyncError(
                "Unable to read Google Sheet; check sharing, sheet ID, tab, and Sheets API access"
            ) from exc

    def append_lead(self, sheet_id: str, tab: str, lead: NormalizedLead) -> bool:
        stage = "connect"
        try:
            with self._service(sheet_id, tab, write=True) as service:
                stage = "read"
                values_api = service.spreadsheets().values()
                quoted = "'" + tab.replace("'", "''") + "'"
                values = (
                    values_api.get(
                        spreadsheetId=sheet_id,
                        range=quoted,
                        valueRenderOption="FORMATTED_VALUE",
                    )
                    .execute(num_retries=2)
                    .get("values", [])
                )
                stage = "validate headers"
                rows = values_to_rows(values)
                new_row = row_for_headers(values[0], lead)
                expected = dict(
                    zip(
                        [str(header).strip().lower() for header in values[0]],
                        new_row,
                        strict=True,
                    )
                )
                matches = [
                    row for row in rows if clean_cell(row.get("external_id")) == lead.external_id
                ]
                if len(matches) > 1:
                    raise SheetIdentityConflict(
                        "La hoja contiene un identificador duplicado. "
                        "Revisa la hoja antes de continuar."
                    )
                if matches:
                    # Same request can be retried after a timeout, partial failure, or restart.
                    if any(
                        clean_cell(matches[0].get(key)) != clean_cell(expected.get(key))
                        for key in (
                            "first_name",
                            "last_name",
                            "phone",
                            "email",
                            "municipality",
                            "lead_date",
                        )
                    ):
                        raise SheetIdentityConflict(
                            "Este envío ya fue guardado con otros datos. "
                            "Revisa la hoja antes de añadir otro lead."
                        )
                    return False
                stage = "append"
                result = values_api.append(
                    spreadsheetId=sheet_id,
                    range=quoted,
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={"majorDimension": "ROWS", "values": [new_row]},
                ).execute(num_retries=0)  # Append is not safe to blindly retry.
                if result.get("updates", {}).get("updatedRows") != 1:
                    raise SheetWriteError(
                        "Google Sheets no confirmó la nueva fila. "
                        "Reintenta este mismo envío para verificarlo."
                    )
                return True
        except (SheetWriteError, SheetIdentityConflict):
            raise
        except Exception as exc:
            logger.error(
                "Google Sheets lead append failed during %s (HTTP %s)",
                stage,
                getattr(getattr(exc, "resp", None), "status", "unknown"),
                extra={"error_type": type(exc).__name__},
            )
            raise SheetWriteError(
                "No se pudo confirmar el lead en Google Sheets. "
                "Reintenta este mismo envío; se comprobará si ya existe."
            ) from exc
