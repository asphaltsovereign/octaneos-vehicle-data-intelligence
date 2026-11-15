# Workshop UI implementation

## Delivered

- Authenticated entry with email/password, explicit demo entry, session expiry handling, bearer storage in `sessionStorage`, and sign-out.
- First-workshop onboarding and workshop selector.
- Responsive job queue with useful counts, lifecycle labels, loading and empty states.
- Customer and motorcycle create/edit forms, demo/source identity fields, and Service Passport access.
- Three-step job-card creation with customer, motorcycle, and complaint validation plus UUID idempotency.
- Saved job detail with editable complaint, technician observations, five-point inspection, lifecycle state, upload classification, CSV/manual analysis, and saved reports.
- Persisted evidence report with immutable evidence presentation, limitations, technician notes, bounded explanation, review transition, and print/PDF layout.
- Vehicle Service Passport timeline backed by the history endpoint.
- Original V3.4 diagnostics lab preserved as `Legacy.tsx`; it is reachable only at `?lab=1` when `/api/config` reports demo mode.

## Integration

All workshop requests use the exact paths and payloads in `docs/API_CONTRACT.md`. Tenant requests include both `Authorization: Bearer …` and `X-Workshop-Id`. Uploads use `FormData` and do not override the browser multipart boundary. No credentials, fake access tokens, or browser-persisted workshop records are included.

## Verification

`npm run build` completed successfully on 2026-09-15. This runs strict TypeScript checking followed by the Vite production build. Output was generated in `frontend/dist` (18 modules transformed).

Live browser integration was not run in this delegated frontend pass because the new backend was being implemented concurrently. The root task owns the end-to-end run.

## Review notes

- External Google font loading is progressive; system fonts remain the fallback if network access is unavailable.
- The current API does not expose a delete operation or a public share URL, so the UI intentionally omits those actions and uses browser print/save-to-PDF.
- Production access to the legacy lab is denied by the `/api/config.demo` gate even if `?lab=1` is present.

## Review correction pass

A second strict build passed after correcting job PATCH payloads, preserving edits before analysis, guarding idempotent job creation, adding inline errors, resetting record-scoped state, preventing tenant-switch result races, adding reviewed and closed lifecycle actions, and including saved technician notes plus quality/model/provenance in print output. Root-level integration owns the browser journey because local shell calls use isolated network namespaces.
