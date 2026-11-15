# Deployment, database and rollback

## Required resources — not provisioned by this release

An authorized Supabase project (Auth and PostgreSQL), a Render Docker web service, a verified email sign-in account, and optionally an OpenRouter key/model. Do not paste secret values into source or conversation logs. Configure environment values through the provider's secret settings. Owner approval is required before provisioning/spend, production migration or deployment.

## Database

1. Take a provider backup before any production change. First validate on a disposable PostgreSQL/Supabase staging database.
2. Set `MIGRATION_DATABASE_URL` in a separate administrative shell. Run `python backend/scripts/migrate.py`. The script tracks `001_workshop` and does nothing if already applied. Startup never migrates.
3. Create a dedicated `sentinel_login` LOGIN role with a generated password using the database admin interface. It must be NOSUPERUSER and NOBYPASSRLS. Grant `sentinel_app` to it and CONNECT to the database. Do not grant table ownership or broad schema rights. Set `DATABASE_URL` to that login, requiring TLS. The app checks the connection role and uses `SET LOCAL ROLE sentinel_app` per transaction.
4. Keep the `sentinel` schema outside Supabase's exposed API schemas. Do not grant access to `anon`, `authenticated`, PUBLIC or service-role clients. All CRUD flows through the authenticated backend. The custom RLS role reads its verified UUID from a transaction-local claim; composite foreign keys prohibit tenant-crossing references.
5. Create/confirm pilot users through Supabase Auth. They sign in and create their workshop from the onboarding UI (up to five workspaces per identity). Additional technician memberships are administrative SQL inserts with verified Supabase user IDs; no invite UI is included.

Use a direct PostgreSQL connection or Supabase's supported session pooler. Validate pooling and role switching before choosing any transaction-pooler configuration. Native concurrency is not established by PGlite tests.

## Application

Build `docker build -t octane-workshop-beta .`; run with `--env-file` pointing at a locally secured production configuration. Render blueprint is `render.yaml`. Required env: OCTANE_ENV=production, OCTANE_DEMO=0, DATABASE_URL, SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY. Optional: OCTANE_AI_PROVIDER, OPENROUTER_API_KEY, OCTANE_AI_MODEL. PORT defaults to 8000. Never configure MIGRATION_DATABASE_URL in the long-running app. Keep one worker/instance for this beta because rate limits and immediate access-token signout denial are process-local. Horizontal scaling requires shared revocation/rate-limit state.

`/health` is process liveness; `/api/ready` verifies security configuration, restricted DB connection and migration. Missing production configuration fails startup. Legacy unscoped lab endpoints are disabled outside explicit demo mode. Production signout invokes Supabase logout and locally blocks the token; verify token expiry/revocation behavior against real Supabase before the pilot.

## Verification commands on staging

- `npm --prefix frontend ci && npm --prefix frontend run build`
- `cd backend` then `python -m pytest -q` with TEST_DATABASE_URL and DATABASE_URL pointing to a disposable migrated database; tests intentionally create synthetic fixtures. Never run tests against customer data.
- Use two real Supabase accounts to verify membership, expired/invalid tokens and signout, and attempt cross-workshop report/job access.
- Run the complete job/report/passport/print journey on desktop and mobile.
- Run a container readiness check and backup restore rehearsal. These gates were not run on hosted infrastructure in this session.

## Backups and rollback

Take encrypted database snapshots and test restore before onboarding real customers. Retain reports, memberships and source hashes together. Restrict backup access. Do not put database dumps in source ZIPs.

For application rollback, redeploy the previous verified image while retaining the database. Migration 001 is additive; do not drop the sentinel schema automatically. A database rollback requires restoring a verified backup in maintenance mode after owner approval; restore it to a separate staging database first and verify reports/history. The archive includes a verified Git bundle so the source checkpoint can be restored independently of a Git host.

## Current boundaries

No external deployment, account creation, production migration, live AI request, or native container verification is claimed. This beta needs a production gate, not a claim of security certification.

## Official references checked

- Supabase verified user: https://supabase.com/docs/reference/javascript/auth-getuser
- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security
- OpenRouter structured outputs: https://openrouter.ai/docs/guides/features/structured-outputs
- PGlite socket and limitations: https://pglite.dev/docs/pglite-socket
