# LeadsPR — FSG Seguros

An agency-branded MVP for a Puerto Rico life insurance lead marketplace. Buyers check out as guests;
eligible leads are randomly allocated only after a verified Stripe payment and delivered by email.

- [Backend setup, configuration, integrations, and operations](backend/README.md)
- [Frontend demo, local commands, presentation flow, and validation](frontend/README.md)

```text
leadspr/
├── backend/
│   ├── app/
│   │   ├── api/{routes,dependencies}/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── integrations/{google_sheets,stripe,email}/
│   │   ├── jobs/
│   │   ├── utils/
│   │   └── main.py
│   ├── alembic/versions/
│   ├── tests/
│   ├── scripts/seed.py
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── .env.example
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── app/{leads,buy,admin,api,checkout/{success,cancel}}/
│   │   ├── components/
│   │   ├── lib/
│   │   ├── types/
│   │   └── services/
│   ├── .env.example
│   ├── package.json
│   ├── package-lock.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── postcss.config.mjs
│   ├── eslint.config.mjs
│   └── README.md
└── README.md
```

Repository-level `.gitignore` excludes secrets, databases, lock files, environments, and build output.

Implemented: the seven-table schema and migration; pricing and eligibility; Sheets parsing and
synchronization; scheduler; guest Checkout; signed webhook fulfillment; Resend delivery and retry;
token-protected admin APIs; audit history; isolated tests. No fake leads are seeded.

The frontend includes a branded homepage, live lead configurator, Stripe test checkout and order
status, and a passcode-protected operations dashboard with real Sheets sync and editable backend-backed prices. The UI uses Puerto Rican Spanish and
a cream/ivory theme with navy text. Prices, inventory,
orders, and sync history come from the existing backend. The frontend guide records the verified
Stripe test payment, lead assignment, Resend test delivery, and Google Sheets synchronization.
