# FSG Seguros — demo frontend

A responsive Next.js App Router / TypeScript frontend for the existing LeadsPR FastAPI backend.
The homepage, agent marketplace, operations dashboard, and checkout return pages share navy,
blue, restrained gold accents, and warm cream/ivory surfaces. All application copy is Puerto Rican
Spanish, with `es-PR` currency/dates and Puerto Rico display time; the company name stays unchanged. Fonts and the homepage photograph are served locally.

## Run the existing demo

Use Node.js 22+ and the already configured backend environment. From the repository root,
run each block in a separate terminal. Skip a server that is already running on its port.

```sh
cd leadspr/backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```sh
stripe listen --events checkout.session.completed,checkout.session.async_payment_succeeded,checkout.session.async_payment_failed,checkout.session.expired --forward-to localhost:8000/api/v1/webhooks/stripe
```

The listener's signing secret must match backend `STRIPE_WEBHOOK_SECRET`. If it changes, update
the ignored backend `.env` and restart FastAPI. Keep `STRIPE_SECRET_KEY` in test mode.
Backend `STRIPE_SUCCESS_URL` should be
`http://localhost:3000/checkout/success?order_id={PUBLIC_ID}` and `STRIPE_CANCEL_URL` should be
`http://localhost:3000/checkout/cancel`.

```sh
cd leadspr/frontend
npm ci
npm run demo:setup
npm run build
npm start -- --hostname 127.0.0.1
```

Open **http://localhost:3000**. Use `npm run dev` instead of build/start while editing.
`demo:setup` copies only the backend admin token into the ignored frontend `.env.local` and generates
a private operations passcode. It preserves existing configured values and prints no credentials.
Open `.env.local` in your editor and use **`DEMO_ADMIN_PASSWORD`** at `/admin`.
You can replace that value with your own passcode of at least 12 characters, then restart Next.js.

Fresh backend setup, dependencies, migrations, and Google access are documented in
[the backend guide](../backend/README.md). This frontend change requires no database migration.

## Configuration and access

| Server-only variable | Purpose |
| --- | --- |
| `BACKEND_API_URL` | FastAPI base, default `http://127.0.0.1:8000/api/v1` |
| `ADMIN_API_TOKEN` | Same token as the backend; forwarded only by the Next.js server |
| `DEMO_ADMIN_PASSWORD` | Private presenter passcode, minimum 12 characters |

Browser requests use same-origin Next.js routes. No Stripe, Google, Resend, database, or admin
secret is needed in browser code. The previous `NEXT_PUBLIC_API_BASE_URL` remains a server-side
fallback for compatibility; new configuration should use `BACKEND_API_URL`.

Operations uses a signed, HTTP-only, SameSite=Strict session lasting eight hours. Cookies are Secure
on HTTPS. Every operations read/write checks the session; mutations also check the request origin.
This is deliberately a local demo passcode gate, without accounts, roles, or a permissions system.
Do not add secrets to any `NEXT_PUBLIC_*` variable.

## Routes and components

| Route | Behavior |
| --- | --- |
| `/` | Agency homepage, value cards, and marketplace introduction |
| `/leads` | Municipality filter, live tier cards, stock-limited quantity, buyer details, order summary, real Stripe test checkout |
| `/buy` | Redirects to `/leads` for old links |
| `/admin` | Passcode sign-in, database totals, inventory, latest eight orders, Sheets sync, inline price editing with fixed ages/read-only exclusions |
| `/checkout/success` | Polls the public order endpoint; shows fulfillment only after the backend confirms it |
| `/checkout/cancel` | Returns the buyer to the marketplace |

Shared components include `Navbar`, `Brand`, `Footer`, `DemoBadge`, `Notice`, `LeadTierCard`,
`QuantitySelector`, `OrderSummary`, `RecentOrders`, `SheetsSyncCard`, `PricingRules`, and `OrderStatus`.
Typed requests remain centralized in `src/lib/api.ts` and `src/services/`.

## Existing backend integration

All paths below use the backend `/api/v1` prefix.

| Backend endpoint | Use |
| --- | --- |
| `GET /inventory/municipalities` | Eligible municipality options |
| `GET /inventory/summary?municipality=...` | Current age ranges, prices, and quantities |
| `POST /checkout` | Existing order creation and Stripe Checkout service |
| `GET /purchases/{public_id}` | Authoritative payment, fulfillment, and email status |
| `PATCH /admin/pricing-rules/{id}` | Existing authenticated price persistence with validation and audit |
| `POST /admin/sync` | Existing Google Sheets synchronization |
| `GET /admin/dashboard` — added | One read-only response composing existing inventory, recent purchases, sync history, and pricing services, plus database count/sum queries |
| `GET /checkout/config` — added | Safe `test`, `live`, or `unconfigured` payment mode; no keys |

The dashboard uses active source rows for Active Leads, the existing eligibility service for
Available Inventory, and all fulfilled orders for order count/revenue (not just the recent eight).
Prices and exclusions are always backend-derived. Existing random allocation, exclusions, and
Stripe webhook behavior remain in the backend. No reservations or allocation logic were added.

The browser's `/api/marketplace/*` proxy permits only the listed public operations. Checkout checks
test mode on the server and validates the Stripe test destination before returning it. The
`/api/operations/{session,dashboard,sync}` and `/api/operations/pricing-rules/[id]` routes keep privileged credentials off the client.

**Nothing in the running application is mocked.** The brand is fictional and the existing leads
are demonstration data. Only automated browser tests use isolated API fixtures, on ports 4318/4319.
Charts, CRM, complex reporting, and full account management remain outside scope.

## Authoritative editable pricing

`PricingRules` sends only `{ price_cents: 2250 }` to the new same-origin
`PATCH /api/operations/pricing-rules/[id]` proxy. It requires the signed admin session and same
origin, rejects extra fields and unsafe/nonpositive/noninteger values, and forwards the server-only
admin token to the existing FastAPI `PATCH /api/v1/admin/pricing-rules/{id}` service.

The existing SQLite `pricing_rules` table stores positive integer cents and audit history. No schema
migration is needed. The editor parses decimal strings into integer cents without floating-point
math and rejects more than two decimals. The dashboard and marketplace fetch this same database
configuration; after saving, the dashboard refreshes. Checkout validates the chosen exact price
and stock against current rules, derives its unit amount from the matching stored rule, and sends
that persisted amount to Stripe. A stale/forged price fails; the marketplace reloads stale pricing.

`purchases.price_per_lead_cents`, `purchases.total_amount_cents`, and
`purchase_leads.price_paid_cents` preserve purchase-time amounts. The order result page reads the
stored unit price and total, never current rules.

The existing inventory/checkout API identifies tiers by exact price. Price PATCH requests reject
a price already used by another active tier, keeping the four age groups distinct. Finish pending
checkouts before changing their tier's price: fulfillment still rechecks current eligibility/pricing
and can flag an older paid checkout for attention. Lead assignment behavior is unchanged.

Shared Spanish errors are in `src/lib/copy.ts`; tier names/locale formatting are in
`src/lib/format.ts`. Theme tokens and responsive editor styling are in `src/app/globals.css`.
No internationalization framework or new runtime dependency was added for this update.

## Presentation flow

1. Open `/`, use **Ver Leads Disponibles**, and choose a municipality.
2. Select an available tier, enter a quantity and demo buyer details, and check the total.
3. Open secure checkout. Use Stripe's test card `4242 4242 4242 4242`, a future expiry, and any CVC.
   Use `delivered@resend.dev` to exercise Resend's delivery test sink, or an allowed inbox you control.
4. Wait for the return page to confirm allocation, then open `/admin` to show the order and totals.
5. Edit the existing test Sheet, wait for it to save, then click **Sincronizar Ahora**. The button stays busy
   while synchronizing and the dashboard reloads after completion. Navigate to `/leads` to see the
   newly available inventory.
6. In **Reglas de Precios**, click **Editar**, enter a price such as `22.50`, and choose **Guardar**
   or **Cancelar**. Refresh `/leads` to see the new price without a rebuild. Age boundaries and
   exclusivity periods stay fixed. Existing completed orders retain their purchased unit price.

## Validation and demo considerations

Verified locally on September 13, 2026:

- All three routes, navigation, 390px mobile layouts, stock validation, immediate totals,
  retry/error states, duplicate-submit protection, passcode access, sign-out, and origin checks.
- The exact pricing regression passed against the connected services: changed Recent leads from
  $20.00 to $22.50 in admin, confirmed $45.00 for two leads in the marketplace and Stripe TEST,
  completed order `ORD-Y8D6WXR4FGUR`, and persisted two allocations at 2250 cents each.
- Changed the tier back to $20.00 through admin after fulfillment. The completed order still
  displays/stores $22.50 per lead and $45.00 total. Resend accepted email to `delivered@resend.dev`.
- Real **Sincronizar Ahora** received/updated 150 rows and refreshed the dashboard successfully.
  The source Sheet itself was not edited during verification.
- Lint, TypeScript, production build, 90 backend tests, and 12 browser scenarios passed.
  Browser scenarios cover price validation, authenticated writes, decimal handling, historical
  totals, Spanish errors, desktop/mobile layouts, WCAG A/AA contrast/semantics, and security.

For Monday, keep FastAPI, Next.js, and the Stripe listener running, with internet access to Stripe,
Google, and Resend. Salinas currently has one Recent lead left after verification: choose Todo Puerto
Rico for a larger order, or add valid test rows and sync. Stripe Checkout uses Latin American Spanish and the FSG product name; the existing
sandbox account name and provider-owned identity disclosure remain controlled by Stripe. Inventory is not reserved during checkout; the return page clearly
flags a paid order whose full quantity is no longer available.

The existing webhook acknowledges successful allocation even when email delivery fails. Such an
order remains fulfilled, with email awaiting confirmation; use the existing admin resend endpoint
if needed. The older regression assertion and backend documentation were aligned with that existing
behavior; fulfillment and delivery logic were not changed.

Run checks from `leadspr/frontend`:

```sh
npm run lint
npm run typecheck
npm run format:check
npm run build
npx playwright install chromium
npm run test:e2e
```

To use installed macOS Chrome instead of downloading Chromium:

```sh
PLAYWRIGHT_CHROME_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm run test:e2e
```

Run backend checks from `leadspr/backend`:

```sh
.venv/bin/ruff check app tests
.venv/bin/pytest -q
```

## Asset credit

Homepage photograph by Hoi An and Da Nang Photographer,
[family walking in a park](https://unsplash.com/photos/a-family-walks-hand-in-hand-on-a-park-path-pXsOE_VcZkc),
used under the Unsplash license. The locally hosted Manrope and Libre Baskerville font packages
include their open-source licenses.


### Añadir Lead

The admin inventory section now includes an expandable `AddLead` form. It posts through the authenticated,
same-origin `/api/operations/leads` proxy to `POST /api/v1/admin/leads`. Google credentials stay on the
backend. The form validates required fields, optional email, phone, municipality, and date; it keeps one
UUID retry key per open draft and blocks repeated submissions. Full success closes/resets the form and
refreshes the dashboard. Confirmed Sheet writes with failed sync show a separate Spanish notice directing
the admin to **Sincronizar Ahora**. Write failures preserve the draft and retry key.

The municipality dropdown reuses the marketplace municipality service with `scope=all`. The shared
backend catalog is based on [US Census Puerto Rico municipios](https://tigerweb.geo.census.gov/tigerwebmain/Files/acs26/tigerweb_acs26_county_pr.html), since eligible inventory alone cannot provide locations for first-time lead entry.

Tests: `tests/e2e/add-lead.spec.ts`; run `npm run test:e2e`. See the
[manual acceptance checklist](../docs/add-lead-acceptance.md) for real Google Sheets verification.

### Recuperación del checkout

La página de estado conserva GET como consulta y usa `POST /api/marketplace/purchases/{public_id}/refresh` cuando falta confirmar el pago o el correo. El proxy exige el mismo origen y no reenvía datos de pago aportados por el navegador. El backend recupera la sesión de Stripe guardada, valida su referencia y reutiliza la asignación y el correo idempotentes. Las consultas aumentan su intervalo y se detienen al terminar o tras 12 intentos, mostrando cómo continuar.

Con `SCHEDULER_ENABLED=true`, el backend recupera hasta 10 órdenes pendientes de los últimos siete días cada minuto, incluso si se cerró el navegador. Mantener los webhooks de Stripe configurados como vía principal; la recuperación es un respaldo para eventos ausentes o envíos fallidos. No hace falta volver a pagar una orden pendiente.
