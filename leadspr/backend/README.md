# LeadsPR backend

FastAPI, SQLAlchemy 2, SQLite, Alembic, Pydantic 2, Google Sheets API v4, Stripe Checkout,
Resend, and APScheduler 3. Python 3.13 is the tested interpreter.

## Install and run

From the repository root, on macOS/Linux:

```sh
cd leadspr/backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env; set ADMIN_API_TOKEN to a random secret of at least 32 characters.
alembic upgrade head
python scripts/seed.py
pytest -q
uvicorn app.main:app --reload --no-access-log
```

Generate an admin token locally with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
Keep it only in your private `.env` or deployment environment. Do not commit that file.

Windows PowerShell:

```powershell
cd leadspr/backend
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env before running integrations.
alembic upgrade head
python scripts/seed.py
pytest -q
uvicorn app.main:app --reload --no-access-log
```

API: http://localhost:8000/api/v1/health. Interactive API reference: http://localhost:8000/docs.
Use the **Authorize** button with your admin token for admin routes. No tables are created at app
startup. Run migrations explicitly before seeding or using the API. No real provider credentials
are required to start the server, inspect empty inventory, or run tests.

## Architecture and ownership

Routes validate requests and call services. Services implement business rules and transaction
boundaries. Repositories contain SQLAlchemy persistence/query operations. Integrations perform
external I/O and are replaceable through `create_app(..., sheets=..., checkout=..., email=...)`.

```text
app/api/routes       Public endpoints and token-protected administration
app/api/dependencies Runtime, read/write sessions, admin authentication
app/core             Configuration, exceptions, JSON logging, service wiring
app/db               Declarative base, UTC timestamp type, engine, transactions
app/models           Exactly seven domain models
app/schemas          Request and response validation
app/repositories     Lead, pricing, purchase, sync, settings, audit, admin persistence
app/services         Pricing, inventory, purchase, fulfillment, sync, email, audit,
                     settings, webhook orchestration, admin queries
app/integrations     Google Sheets v4 client/parser, Stripe SDK, Resend HTTP adapter/template
app/jobs             Lifespan-managed daily sync scheduler
app/utils            UTC clock and business calendar date
alembic/versions     Initial explicit schema migration
scripts/seed.py      Idempotent pricing and non-secret configuration seed
tests                Unit, API, transaction, concurrency, migration, adapter, scheduler tests
```

Google Sheets owns raw lead fields. Synchronization changes these fields plus source activity and
sync timestamps. SQLite owns purchases, allocations/exclusions, settings, pricing, sync history,
and audit history. Missing upstream leads become inactive; they are never deleted. Purchase
relationships are preserved with restrictive foreign keys.

The database has `leads`, `pricing_rules`, `purchases`, `purchase_leads`, `app_settings`, `sync_runs`,
and `audit_logs`. Alembic also maintains its technical `alembic_version` table. There are no user,
buyer, reservation, refund, or subscription tables. Prices and ages are never stored on leads.

Money is integer USD cents. Lead age uses calendar dates in the configured business timezone,
defaulting to `America/Puerto_Rico`. Timestamps cross ORM boundaries as timezone-aware UTC;
SQLite persists them as UTC without an offset.

## All environment variables

Load `.env` from the backend working directory. Environment variables override `.env` values.
Secrets are `SecretStr` values and are never returned by the settings API.

| Variable | Default / purpose |
| --- | --- |
| `APP_ENV` | `development`; also `test` or `production` |
| `DATABASE_URL` | `sqlite:///./leadspr.db`; relative to backend working directory |
| `FRONTEND_URL` | `http://localhost:3000`; exact allowed CORS origin |
| `ADMIN_API_TOKEN` | Empty; set a strong random token of at least 32 characters |
| `GOOGLE_SHEETS_CREDENTIALS_JSON` | Empty; complete service account JSON as a single-line string |
| `GOOGLE_SHEET_ID` | Empty; spreadsheet ID from its URL |
| `GOOGLE_SHEET_TAB` | `Leads`; exact worksheet/tab title |
| `STRIPE_SECRET_KEY` | Empty; Stripe secret key, use test mode first |
| `STRIPE_WEBHOOK_SECRET` | Empty; signing secret from Stripe CLI or the deployed webhook endpoint |
| `STRIPE_SUCCESS_URL` | `http://localhost:3000/checkout/success?order_id={PUBLIC_ID}` |
| `STRIPE_CANCEL_URL` | `http://localhost:3000/checkout/cancel` |
| `RESEND_API_KEY` | Empty; Resend API key permitted to send from your domain |
| `EMAIL_FROM` | Empty; verified sender address, e.g. `orders@your-domain.com` |
| `APP_TIMEZONE` | `America/Puerto_Rico`; valid IANA timezone |
| `DAILY_SYNC_TIME` | `02:00`; local business time in HH:MM format |
| `SCHEDULER_ENABLED` | `true`; use `false` for a process that should not schedule jobs |

The frontend has one separate public variable: `NEXT_PUBLIC_API_BASE_URL`, default
`http://localhost:8000/api/v1`. Backend secrets must never be copied into frontend environment files.

The only editable database settings are `google_sheet_id`, `google_sheet_tab`, `daily_sync_time`,
`timezone`, `company_name`, and `sender_email`. **Stored app settings override environment defaults
for those values.** Set integration defaults before the first seed, or use `PATCH /admin/settings`
afterward. Re-running the seed preserves existing settings and pricing edits.

## Database, migrations, and seeding

```sh
alembic upgrade head
python scripts/seed.py
alembic current
alembic check
```

The seed creates these active ranges only when pricing is empty:

| Age in days | Price | Exclusion |
| --- | --- | --- |
| 0–7 | 3000 cents | 30 days |
| 8–30 | 2000 cents | 20 days |
| 31–60 | 1200 cents | 10 days |
| 61+ | 500 cents | 5 days |

It never inserts example leads. For future schema changes, modify the models, run
`alembic revision --autogenerate -m "describe change"`, inspect the generated migration, and then
apply it. Keep migrations self-contained; render custom UTC model types as `sa.DateTime(timezone=True)`
in migrations. Back up an existing SQLite database before changing its schema. The initial migration
has a tested downgrade, but downgrading to `base` removes the domain tables and their data.

Active pricing must cover every nonnegative age exactly once, beginning at 0 and ending with an
open-ended range. Single POST/PATCH operations reject gaps and overlaps. The small additional
`PUT /admin/pricing-rules` endpoint supports atomic edits to adjacent ranges: submit a JSON list
of complete rules, include every existing ID exactly once, and use `id: null` for a new rule.
Deactivate obsolete rules in the same request that introduces their replacements. Existing IDs
are preserved for history. Inactive rules may overlap. Legacy full-configuration operations support
equal prices, which inventory aggregates into one exact-price tier. Price PATCH updates reject a
price already used by another active rule so the four age tiers remain distinct in the admin editor.

The frontend admin editor sends only positive integer `price_cents` through its authenticated
server proxy; ages and exclusions stay read-only. Existing strict integer validation rejects zero,
negative, fractional, string, boolean, and null values. Checkout validates the selected exact price
against current inventory and uses the matching database rule to persist integer unit/total amounts.
Stripe receives that stored unit amount and uses `es-419` for its hosted form. Historical purchases
and allocations keep their stored prices after edits. Complete pending payments before changing
prices: the existing fulfillment service rechecks current pricing and eligibility at payment time.

## Connect your Google Sheet

1. Create or choose a Google Cloud project and enable **Google Sheets API**.
2. Create a service account in that project and create its JSON key. This service does not need
   Google Workspace domain-wide delegation. Keep the downloaded key outside the repository.
3. Open the spreadsheet and share it with the key's `client_email` address as an **Editor** to enable admin lead entry (Viewer remains sufficient for sync only).
4. Put canonical headers in row 1. Required: `external_id`, `lead_date`, `first_name`, `phone`.
   Optional: `last_name`, `email`, `municipality`, `insurance_type`, `source`, `campaign`,
   `language`, `notes`. Header whitespace/case is normalized; field names use underscores.
5. Give every row a permanent, unique `external_id`. Do not use row numbers or formulas that change
   IDs when rows move. Format identifiers and phones as plain text to preserve leading zeros and `+`.
   Format dates to display as `YYYY-MM-DD`; the API reads formatted cell values.
6. In `backend/.env`, set `GOOGLE_SHEET_ID` to the part between `/d/` and `/edit` in the spreadsheet URL,
   and set `GOOGLE_SHEET_TAB` to the exact tab title. A tab's numeric `gid` is not its title.
7. Set `GOOGLE_SHEETS_CREDENTIALS_JSON` to the **complete JSON object**, serialized to a single line.
   Keep private-key newlines escaped as `\n` inside JSON. In `.env`, wrap the JSON in single quotes.
   You can create a local one-line representation with
   `python -c "import json; print(json.dumps(json.load(open('/absolute/path/service-account.json'))))"`.
   Paste the result only into your local secret configuration.
8. Run migrations and the seed, then start FastAPI. If you seeded earlier, use the authorized
   settings API to set `google_sheet_id` and `google_sheet_tab` to your actual values.
9. In `/docs`, authorize with `ADMIN_API_TOKEN`, invoke `POST /api/v1/admin/sync`, then inspect
   `/api/v1/admin/sync-runs`, `/api/v1/admin/leads`, and the public inventory summary.

Synchronization uses the read-only Sheets scope and reads the complete configured tab, including rows hidden by UI filters. Admin lead entry uses the `spreadsheets` write scope with the same service account and configured worksheet. Both scopes are documented in [Google Sheets API scopes](https://developers.google.com/workspace/sheets/api/scopes).

### Add one lead from admin

`POST /api/v1/admin/leads` requires the existing admin bearer token and a UUID `Idempotency-Key` header.
Accepts `first_name`, optional `last_name`, `phone`, optional `email`, `municipality`, and ISO `lead_date`.
Unknown fields are rejected. Municipality is checked against the shared Puerto Rico catalog exposed by
`GET /inventory/municipalities?scope=all`; the default endpoint continues to list eligible inventory only.

The service generates `LEAD-<uppercase UUID hex>`, checks the actual sheet for that ID, and appends using
its current normalized header order with `RAW` values and no automatic append retries. The unused `id`
column stays blank; `insurance_type=Life Insurance`, `source=Admin`, `language=es`, and blank campaign
are system-managed. Dates and phones remain strings, preserving leading zeros and `+`. No lead is
written directly to SQLite: the existing `LeadSyncService.sync(manual=True)` imports the appended row.

A 201 response includes `external_id`, `sheet_written`, `appended`, `status` (`synced` or `sync_pending`),
`available`, and `sync_run`. A pending sync is a confirmed Sheet write: use Sync Now, not another new
submission. Retrying with the same key checks for the existing row and never blindly appends it again.
A key reused with conflicting contact data returns 409. An uncertain write returns 502 with a safe
Spanish message; retry the same request/key to check whether Google accepted it.

A local file lock serializes lead entry across processes sharing this SQLite database. Multiple hosts
would require a distributed lock before deploying concurrent writers. Do not rearrange Sheet headers
while someone is submitting a lead. Full acceptance steps are in [the add-lead checklist](../docs/add-lead-acceptance.md).

Every attempt creates a sync run, including missing credentials, overlapping runs, and upstream
failures. Blank insurance types become `Life Insurance`. Future dates may be synchronized but are
never offered for sale. Malformed optional email values are discarded and recorded as warnings.
Required-field errors are recorded using row numbers and field names, without contact values.

A run with rejected required rows applies its valid rows, reports `FAILED`, and suppresses all
deactivation for that run. Correct the source and synchronize again. Duplicate IDs or invalid/missing
headers abort before changing leads. A valid header-only sheet is an intentional empty snapshot
and deactivates every active local lead. An API response with no headers fails safely.

Counts: `leads_updated` includes reactivated existing leads; `leads_reactivated` is that subset.
`rows_received` counts physical rows returned after the header, including interior blank rows.
Optional warnings and rejected-row details are serialized in `sync_runs.error_message`.

## Stripe Checkout and signed webhooks

1. Set a Stripe test secret key in `STRIPE_SECRET_KEY`.
2. Set success/cancel URLs to frontend routes. `{PUBLIC_ID}` in the success URL is replaced server-side.
3. Start FastAPI. Install/sign into the Stripe CLI and run:

```sh
stripe listen --events checkout.session.completed,checkout.session.async_payment_succeeded,checkout.session.async_payment_failed,checkout.session.expired --forward-to localhost:8000/api/v1/webhooks/stripe
```

4. Copy the CLI's `whsec_...` signing secret into `STRIPE_WEBHOOK_SECRET` and restart FastAPI.
5. Synchronize eligible leads, then create a Checkout session through `/docs` or an HTTP client:

```json
{
  "buyer_name": "Test Buyer",
  "buyer_email": "your-test-inbox@example.com",
  "insurance_type": "Life Insurance",
  "municipality": "Bayamón",
  "price_per_lead_cents": 2000,
  "quantity": 1
}
```

Use a real inbox you control for end-to-end verification. Open the returned Checkout URL and use
[Stripe's test payment methods](https://docs.stripe.com/testing). Generic `stripe trigger` fixtures
do not refer to an application order and are intentionally ignored; test an actual app-created session.

For deployment, register `https://your-api-domain/api/v1/webhooks/stripe` with those four event types
and configure that endpoint's signing secret. The CLI secret and deployed endpoint secret differ.

Checkout calculates the total, persists a PENDING order, then calls Stripe. Metadata contains only
the public order reference. There are no reservations or pre-payment allocations. A Checkout API
failure marks a still-PENDING order FAILED; a later authoritative success can recover it.

Payment success requires a verified signature and `payment_status=paid`. The order reference,
Checkout ID, payment intent, USD currency, amount, and payment mode are checked. Unpaid completions
wait for `async_payment_succeeded`; session expiry/async failure marks a PENDING order FAILED.
Individual recoverable card-attempt failures do not terminate a Checkout session. Unknown event types
and Checkout events without LeadsPR metadata are acknowledged without mutation.

Inside one write transaction, fulfillment rechecks current date, active pricing, source activity,
municipality, insurance type, and all unexpired exclusions. It selects exactly the paid quantity at
the paid price or allocates none. Each allocation stores the current rule ID, historical cents paid,
and the rule's exclusion duration at allocation time. A shortage or changed tier produces
FULFILLMENT_FAILED with payment details and an audit entry. This state is terminal for automatic
processing; repeated webhooks do not silently allocate later. Admin handling is manual; automatic
refunds and a fulfillment-retry UI are outside this MVP.

## Resend delivery and retry

Verify your sending domain in Resend, set `RESEND_API_KEY` and `EMAIL_FROM`, and ensure the receiving
address is permitted by your Resend account's current sending mode. Database `sender_email`, when
present, overrides `EMAIL_FROM`. Delivery includes the order, quantity, amount, and purchased lead
contact/source/campaign/language/notes fields, with escaped HTML and a plain-text alternative.

Resend is called only after allocation commits. `email_sent_at` means the provider accepted the send;
it does not prove inbox delivery. A send failure leaves the purchase FULFILLED, preserves its prior
email timestamp (null for initial failure), and records an audit/log error. The existing webhook
acknowledges completed allocation with HTTP 200 even when delivery fails. Stripe therefore does not
automatically retry that email failure. Explicit event redelivery can retry delivery without
reallocation; the admin resend endpoint below is available for deliberate retries.

Use `POST /api/v1/admin/purchases/{public_id}/resend-email` to deliberately resend. Supply an
`Idempotency-Key` header containing 8–100 letters, digits, `_`, or `-`. Reuse it when retrying the same
request; use a new key for a new deliberate resend. Successful resend keys are recorded in existing
audit history, so duplicate requests are skipped locally as well as at Resend.

Initial delivery uses a stable per-order provider idempotency key. Resend retains keys for
[24 hours](https://resend.com/docs/dashboard/emails/idempotency-keys). A process crash after provider
acceptance but before the local commit can still cause a duplicate after that window; exactly-once
external email delivery is not claimed. Resend rejects reuse of a key with a changed payload. If
raw lead/settings edits change the payload during an uncertain retry, inspect provider delivery
history and use an explicit new admin resend key when appropriate.

The seven-table schema keeps historical prices/exclusions but does not snapshot raw contact fields.
Admin order detail and resends read current Sheet-owned lead data. No additional snapshot entities
have been added.

## Scheduling, transactions, and deployment limits

APScheduler starts/stops with FastAPI lifespan and uses a daily cron trigger in the business timezone.
The owner refreshes database time/timezone settings every 60 seconds. The scheduler does not run a
sync on startup; invoke manual sync for the first import. Run continuously if daily synchronization
is needed; missed executions while the app is stopped are not stored in a persistent job queue.

SQLite uses foreign keys, WAL mode, a 30-second busy timeout, and explicit transaction control.
Every mutation service uses `BEGIN IMMEDIATE` before its reads. This serializes competing allocations,
pricing edits, and sync updates across processes sharing the same local database. Test coverage
includes simultaneous payments competing for one lead and duplicate concurrent fulfillment.

File locks next to the database prevent duplicate local scheduler owners during overlapping reloads
and prevent overlapping manual/scheduled sync snapshots. The scheduler lock can be released safely
when lifespan shutdown runs on a different thread. Run one API worker for this MVP. There is no
multi-host scheduler election or failover. Interrupted syncs may remain RUNNING in history;
a later process can start a new attempt because OS locks are released when the old process exits.

Email attempts are serialized with a SQLite write lock during the provider request, using an HTTP
timeout of 15 seconds per phase. This is a deliberate low-volume MVP tradeoff to avoid another queue
or outbox table. Other writers can wait while email sends. Checkout and Sheets network reads happen
outside allocation transactions.

SQLAlchemy models, integer money, Python date boundaries, and repository-isolated random selection
make migration to another database straightforward. PostgreSQL is **not** claimed concurrency-ready:
before switching, add row/advisory locks for allocation and rule changes, replace the local scheduler
coordination as needed, review generated boolean defaults, install the driver, and run the transaction
tests against PostgreSQL. SQLite-specific write locking is isolated in `app/db/session.py`.

Use persistent local storage for SQLite and its adjacent lock/WAL files, a single running host,
HTTPS at your reverse proxy, and exact frontend origins. The example server command disables access
logs so admin filters containing buyer email are not written as URL query strings. Configure any
reverse-proxy access logs similarly. Application logs are JSON and omit raw provider errors,
webhook payloads, credentials, and lead/buyer contact fields. Public order responses use an explicit
allowlist and expose no internal sequential IDs or contact information. Admin APIs use a shared bearer
token with constant-time comparison; a complete admin sign-in/session system is deferred.

## API overview

Every route is under `/api/v1`. Responses are JSON; collections expose aggregates or bounded pages.
Public IDs contain 12 random characters from an unambiguous alphabet after `ORD-`.

| Method / path | Behavior |
| --- | --- |
| `GET /health` | API/database/schema connectivity |
| `GET /inventory/summary` | Counts per active exact price, optional municipality and insurance type |
| `GET /inventory/municipalities` | Municipalities with eligible inventory |
| `GET /checkout/config` | Safe payment mode (`test`, `live`, or `unconfigured`); no keys |
| `POST /checkout` | Validate inventory, calculate total, create order and Stripe Checkout |
| `GET /purchases/{public_id}` | Safe order status, quantity, money, timestamps; no buyer/lead PII |
| `POST /webhooks/stripe` | Raw-body signature verification and idempotent payment handling |
| `GET /admin/dashboard` | Active/eligible totals, all fulfilled order totals, latest eight purchases, latest sync, and active pricing rules |
| `GET /admin/leads` | Filtered lead page with computed age/price/exclusion |
| `GET /admin/pricing-rules` | Current rules |
| `POST /admin/pricing-rules` | Create a rule while preserving valid active coverage |
| `PATCH /admin/pricing-rules/{id}` | Edit a rule with validation and audit |
| `PUT /admin/pricing-rules` | Atomic full configuration update for adjacent age ranges |
| `POST /admin/sync` | Synchronous manual Sheets synchronization |
| `GET /admin/sync-runs` | Recent run history, offset/limit |
| `GET /admin/purchases` | Filtered purchase history, offset/limit |
| `GET /admin/purchases/{public_id}` | Buyer/payment information and allocated leads |
| `POST /admin/purchases/{public_id}/resend-email` | Resend fulfilled order; Idempotency-Key required |
| `GET /admin/settings` | Effective non-secret settings |
| `PATCH /admin/settings` | Whitelisted setting changes with audit |

Admin lead filters: `external_id`, `municipality`, `source_active`, `price_cents`, `min_age_days`,
`max_age_days`, `offset`, `limit`. Purchase filters: `status`, `buyer_email`, `public_id`,
`created_from`, `created_to`, `offset`, `limit`. Date filters require offset-aware ISO timestamps;
`created_from` is inclusive and `created_to` exclusive. Pages default to 50 with a maximum of 200.

Errors have this shape:

```json
{"error":{"code":"insufficient_inventory","message":"Requested quantity is unavailable; 0 eligible"}}
```

Business validation uses 400, missing resources 404, conflicts 409, schema validation 422,
unexpected errors 500, provider failures 502, and missing integration configuration 503. Unauthorized
admin requests use 401. No response exposes raw exception traces. Validation errors include sanitized
locations and descriptions. Provider failures are intentionally phrased for an operator to act on.

## Testing and verification scope

```sh
pytest -q
ruff check app tests scripts alembic
ruff format --check app tests scripts alembic
alembic check
```

Tests use temporary SQLite databases and fake external clients. Signed webhook tests use local HMAC
signatures and the actual Stripe signature verifier. Adapter contract tests inspect request arguments
without making provider requests. Migration tests upgrade/downgrade/upgrade a fresh database and
assert exactly seven domain tables. Scheduler tests verify local ownership and cross-thread shutdown.

Fully implemented backend paths: configuration, models, migrations, seeding, dynamic pricing and
range edits, eligibility, sync/parser/history, daily scheduling, guest Checkout, signed webhooks,
atomic exact fulfillment, exclusions, historical pricing, Resend email/retry, token-protected admin
APIs, audit history, errors, and CORS.

Deferred: buyer frontend flow, frontend order-status integration, admin frontend/sign-in, operational
handling of FULFILLMENT_FAILED orders, refunds, multi-host deployment coordination, and high-volume
delivery queues. These have not been disguised as working features.

No live Google Sheet read, Stripe payment, or Resend send has been verified with your accounts.
Configure credentials and perform the setup steps above before claiming an end-to-end live purchase.
