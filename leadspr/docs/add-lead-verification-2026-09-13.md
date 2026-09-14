# Añadir Lead: verification after Editor access

Verified 2026-09-13 against `leadspr_150_fake_leads`, worksheet `Leads`.

**The Google Sheets HTTP 403 blocker is resolved. The Añadir Lead workflow is ready for manual acceptance testing.**

No application code changes were needed. Two deliberately fake leads were retained for manual inspection.

| Test | Name | External ID | Email | Phone |
| --- | --- | --- | --- | --- |
| Backend API | Prueba API badf8178 Editor Demo | `LEAD-BADF817811664F42900C857D9D3E54D4` | prueba-api-editor-badf8178@example.com | `+19395550101` |
| Admin UI | Prueba UI badf8178 Editor Demo | `LEAD-3378231C7EFB4C57A829D03B13687B07` | prueba-ui-editor-badf8178@example.com | `+19395550102` |

Both records use date `2026-09-13`, municipality `Salinas`, stored insurance type `Life Insurance`,
source `Admin`, and language `es`. The existing `id` and `campaign` columns remain blank.
All values were read back from the physical Sheet and checked against the submitted payload and header mapping.

| Measure | Before | After API lead | After UI lead and restart |
| --- | ---: | ---: | ---: |
| Sheet data rows, excluding header | 150 | 151 | 152 |
| Active leads | 150 | 151 | 152 |
| Available inventory | 132 | 133 | 134 |
| Fresh / 0–7 day inventory | 30 | 31 | 32 |
| Salinas fresh inventory | 2 | 3 | 4 |

## Verified behavior

- Authenticated API create returned 201, `appended=true`, `status=synced`, `available=true`.
- First append invoked the existing sync: 1 created, 150 updated. UI append: 1 created, 151 updated.
- The implementation still enters Google Sheets first, then calls `LeadSyncService.sync(manual=True)`;
  inspection confirmed no separate direct-database creation path.
- Both exact external IDs occur once in the Sheet and once in SQLite. Both have `age_days=0`,
  `current_price_cents=4000`, and no current exclusion. Classification and pricing were not overridden.
- Exact request/key retry returned `appended=false` and created 0 new database leads.
- Normal sync created 0 new leads. The isolated backend was stopped and restarted against the same
  database and Sheet; sync then reported 152 received, 0 created, 152 updated.
- Retrying both original request keys after restart still appended nothing. The Sheet ended with
  152 distinct external IDs across 152 data rows.
- The real admin UI showed loading protection, success feedback, closed/reset the form, and updated
  dashboard and tier counts without a page reload. A double-click plus a repeated submit event generated
  exactly one POST. `/leads`, including its Salinas filter, reflected the additional inventory.

## Validation and logs

- Ruff passed; 111 backend tests passed. Two existing dependency deprecation warnings remain.
- Frontend lint, TypeScript checks, and production build passed.
- All 23 browser/E2E tests passed using isolated fixtures.
- Live application logs contained no Google 403, authentication failures, malformed-row errors,
  unhandled exceptions, duplicate sync inserts, or credential leakage.
- A separate browser resource request for `/favicon.ico` returned 404. This existing, nonblocking
  cosmetic issue was reported without changing application code. All live lead-entry assertions passed.

The two Sheet rows were intentionally left in place as requested. Temporary acceptance servers were
used on ports 4329/4330; the existing development servers were not stopped.
