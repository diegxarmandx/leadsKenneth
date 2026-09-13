import json
from typing import Any, Protocol

import google_auth_httplib2
import httplib2
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.core.config import Settings
from app.core.exceptions import ConfigurationError, SheetSyncError
from app.integrations.google_sheets.parser import values_to_rows


class SheetClient(Protocol):
    def fetch_rows(self, sheet_id: str, tab: str) -> list[dict[str, Any]]: ...


class GoogleSheetsClient:
    def __init__(self, config: Settings) -> None:
        self.config = config

    def fetch_rows(self, sheet_id: str, tab: str) -> list[dict[str, Any]]:
        secret = self.config.google_sheets_credentials_json.get_secret_value()
        if not secret or not sheet_id or not tab:
            raise ConfigurationError(
                "Configure GOOGLE_SHEETS_CREDENTIALS_JSON, GOOGLE_SHEET_ID, "
                "and GOOGLE_SHEET_TAB before synchronization"
            )
        try:
            credentials = Credentials.from_service_account_info(
                json.loads(secret),
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise ConfigurationError("Google service account JSON is invalid") from exc
        try:
            http = google_auth_httplib2.AuthorizedHttp(credentials, http=httplib2.Http(timeout=30))
            with build("sheets", "v4", http=http, cache_discovery=False) as service:
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
        except SheetSyncError:
            raise
        except Exception as exc:
            raise SheetSyncError(
                "Unable to read Google Sheet; check sharing, sheet ID, tab, and Sheets API access"
            ) from exc
