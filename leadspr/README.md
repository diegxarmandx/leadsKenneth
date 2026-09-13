# LeadsPR

Backend-first MVP for a Puerto Rico life insurance lead marketplace. Buyers check out as guests;
eligible leads are randomly allocated only after a verified Stripe payment and delivered by email.

- [Backend setup, configuration, integrations, and operations](backend/README.md)
- [Frontend scaffold](frontend/README.md)

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
│   │   ├── app/{buy,admin,checkout/{success,cancel}}/
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

Frontend pages are intentional placeholders. There is no buyer form, live order-status UI, admin
sign-in UI, or dashboard. Google, Stripe, and Resend adapters are implemented and tested with local
fakes/mocks; live external operation requires your credentials and has not been verified.
