# Admin lead entry acceptance

## Configuration

Use the existing backend and frontend env files. The configured test spreadsheet inspected for this work is
`leadspr_150_fake_leads`, worksheet `Leads`. The Google service account must have Editor access. No new
credentials, database schema, pricing rules, or aging logic are required.

The actual worksheet header order is:

| Column | Written value |
| --- | --- |
| `id` | Blank; unused by the importer |
| `external_id` | `LEAD-` plus the uppercase hexadecimal UUID retry key |
| `lead_date` | Selected ISO `YYYY-MM-DD` date |
| `first_name` | Nombre |
| `last_name` | Apellido, or blank |
| `phone` | Validated text, preserving leading zeros and `+` |
| `email` | Validated email, or blank |
| `municipality` | Selected official Puerto Rico municipality |
| `insurance_type` | `Life Insurance` |
| `source` | `Admin` |
| `campaign` | Blank |
| `language` | `es` |

The adapter reads and validates the headers on every submission and maps by name, so reordered columns
are supported. Unknown columns stay blank. Missing required headers or missing columns for supplied
contact data fail before append. Do not change headers during an in-flight submission.

## Exact manual steps

1. Start the backend from `leadspr/backend`: `.venv/bin/uvicorn app.main:app --reload --port 8000`.
2. Start the frontend from `leadspr/frontend`: `npm run dev`.
3. Open `http://localhost:3000/admin` and sign in with the configured demo password.
4. Note **Leads Activos**, **Inventario Disponible**, and the **Leads Nuevos** tier count.
5. Click **Añadir Lead**. Confirm Seguro de Vida is fixed and the date defaults to the dashboard's business date.
6. Fill Nombre `Prueba de formulario`, Apellido `Demo Codex`, Teléfono `+1 (787) 555-0199`,
   Correo `lead-demo@example.com`, Municipio `Salinas`, and today's date. Use only fictitious data.
7. Click **Guardar Lead** once. Confirm the button shows **Añadiendo lead...** and blocks repeated clicks.
8. Confirm **Lead añadido y sincronizado correctamente.** and that the form closes. Note the response's
   `external_id` in the browser Network panel if needed for verification.
9. Open the configured test Google Sheet, tab `Leads`. Locate that exact `external_id`; verify all values
   and that only one physical row has that ID.
10. Return to admin. Confirm active and available totals each increased by one and the 0–7 day tier increased
    by one, assuming the current date is covered by an active pricing rule.
11. Open `/leads`. Confirm the same inventory change, including when filtering for Salinas.
12. Return to `/admin`, click **Sincronizar Ahora**, and confirm no second lead appears.
13. Stop/restart the backend, keeping the same SQLite database and Google Sheet configuration. Sync again.
14. Search the same external ID in the Sheet and authenticated `GET /api/v1/admin/leads?external_id=...`.
    Confirm exactly one Sheet row and one local lead remain.

## Failure checks

- Use the automated fixture tests for write failure and sync failure; do not deliberately damage the demo sheet.
- A confirmed Sheet write followed by sync failure closes the form and instructs **Sincronizar Ahora**.
  The lead must never be appended again to recover synchronization.
- A write timeout can be ambiguous. Keep the form open and retry that same draft: its request key remains
  stable. Check the Sheet before discarding an uncertain draft or re-entering it in a new tab, since a new
  draft intentionally represents a new lead.
- New-source IDs are stable across syncs and backend restarts. This is request deduplication, not contact
  deduplication: two intentionally separate submissions with identical contact data create separate IDs.

## Automated validation

- Backend: `.venv/bin/pytest -q` and `.venv/bin/ruff check app tests`.
- Frontend: `npm run lint`, `npm run typecheck`, `npm run build`, `npm run test:e2e`.
- New backend coverage: `tests/test_lead_entry.py`.
- New browser coverage: `tests/e2e/add-lead.spec.ts`.

## Initial verification before Editor access

**Update:** Editor access resolved the blocker. See the [successful live retest](add-lead-verification-2026-09-13.md).

The following records the initial result on 2026-09-13:

- 111 backend tests passed; Ruff passed.
- Frontend lint, TypeScript checks, and production build passed.
- All 23 browser tests passed, including four new lead-entry scenarios and existing checkout, sync,
  pricing, cancellation, and accessibility checks.
- The form was visually inspected using the real admin dashboard and configured test services.
- The real Sheet can be read, but Google returned HTTP 403 during `values.append`. Write-scope
  authentication succeeds; permission to append does not. The service account is
  `leadstest-backend@leadstest-508419.iam.gserviceaccount.com`.
- The test Sheet still has 150 rows; neither failed attempt created the fake test lead or a local row.
- Live full-success, inventory-increase, subsequent-sync, and backend-restart acceptance steps remain
  pending until the service account has Editor access and any applicable tab/range protection allows it.
  This is the remaining demo blocker. The same behaviors pass with the isolated automated test adapters.
