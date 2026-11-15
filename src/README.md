# Source map

The implementation keeps its recovered layout so imports, launchers and tests remain reproducible.

| Directory | Responsibility |
|---|---|
| `backend/app/services` | CSV ingestion, features, statistical screening, rules and investigation |
| `backend/app/workshop` | Membership, records, saved evidence, notes and bounded explanation |
| `backend/migrations` | Recovered PostgreSQL schema and policies |
| `backend/tests` | API, model, data-contract, workflow and isolation checks |
| `frontend/src/workspace` | Current Local 0.2 evidence interface and charts |
| `frontend/src/Legacy.tsx` | Earlier laboratory demonstration |
| `tools` | Local database, launcher and verification harness |

No duplicate implementation is placed under `src/` merely to change the folder shape.
