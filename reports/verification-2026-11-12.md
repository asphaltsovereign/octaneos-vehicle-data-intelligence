# Consolidation verification — 12 November 2026

Source: recovered Local 0.2 imported above original Git commit `025215d4f2faa24d923f8906a0841b08f974eeaf`. Environment: Linux, Python 3.12.14, Node.js 24.22.1; supplied Python/npm lockfiles installed.

| Check | Actual result |
|---|---|
| `.venv/bin/python tools/verify-local.py` | Exit 0; 64 passed, one existing Starlette/AnyIO deprecation warning; 65.59 seconds |
| `npm --prefix frontend run build` | Exit 0; TypeScript check and Vite production build pass |
| `node --test tools/chart-math.test.mjs` | Exit 0; 4 passed, 0 failed |
| `.venv/bin/python -m pip check` | No broken requirements found |
| Both location-free synthetic CSV examples | Import as VED-shaped input; 120 rows each, analysis-ready, quality score 90, zero non-null latitude/longitude values |
| Recovered SAN bench example into the importer | Rejected as expected; confirms the documented contract mismatch |
| New browser end-to-end run | Not run; screenshots are recovered September captures |
| Frozen artifact and historical ML benchmark | Binary absent; training and held-out evaluation not rerun |
| Hosted identity/native PostgreSQL/Windows/Docker/real vehicle | Not run |

Synthetic sample SHA-256:

- `normal.csv`: `2ed0c40f5bf783a3a42f2dd24db2e8e5ab03031cc50006b1e176a9afb23b665b`
- `voltage_degradation.csv`: `ca910eb0254754f926e3f968d65de4c6461d73f1a02b8c1a061142e9b774484f`

Raw consolidation command logs are retained in `verification/CONSOLIDATION_*_2026-11-12.log` in the handoff package. Existing ignore rules keep transient `.log` files out of Git; this report records the command results. The earlier release reports remain historical records. No source behavior was changed during this consolidation.

## Clean Git clone startup

A clean clone from the prepared Git bundle installed the locked Python dependencies, installed database/frontend npm dependencies, built the frontend, and started `tools/run-demo.py`. `/health`, `/` and `/model/info` returned HTTP 200. The root served built assets and the API correctly reported the frozen artifact missing. This is an HTTP startup/static-UI smoke check, not a browser end-to-end test. No real customer records or external providers were used.
