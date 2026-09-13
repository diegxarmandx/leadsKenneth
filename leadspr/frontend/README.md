# LeadsPR frontend

Minimal Next.js App Router, TypeScript, and Tailwind CSS scaffold. The backend is the current priority.
Pages use Server Components and work without the API running.

## Run locally

Use Node.js 22 or newer supported LTS and npm. From the repository root:

```sh
cd leadspr/frontend
cp .env.example .env.local
npm ci
npm run dev
```

Open http://localhost:3000. On Windows PowerShell use `Copy-Item .env.example .env.local`.

```sh
npm run lint
npm run typecheck
npm run build
npm start
```

## Configuration

`NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1` points to FastAPI. This is a public build-time
value. Never add backend tokens or provider secrets to a `NEXT_PUBLIC_*` variable. Set this URL before
building for another environment and update backend `FRONTEND_URL` to the actual frontend origin.

## Routes

| Route | Current behavior |
| --- | --- |
| `/` | Basic LeadsPR introduction |
| `/buy` | Buyer-flow placeholder |
| `/checkout/success` | Placeholder; never treats a redirect as payment confirmation |
| `/checkout/cancel` | Checkout exit page |
| `/admin` | Static placeholder containing no administrative data |

`src/lib/api.ts` provides uncached JSON requests, typed API errors, and a timeout.
`src/types/api.ts` and `src/services/marketplace.ts` define public inventory, Checkout, and order-status
contracts for the future UI. They are not called automatically by the placeholder pages.

Admin authentication is enforced by the backend. A future admin UI must use an appropriate sign-in
and server-side session design; do not ship the shared admin token to browser code.
