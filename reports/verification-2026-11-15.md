# Publication verification — 15 November 2026

Checks rerun on the restored Local 0.2 source before publishing under `asphaltsovereign`.

- `.venv/bin/python tools/verify-local.py`: exit 0, **64 passed** in 59.80 seconds using disposable PostgreSQL/WASM. One dependency deprecation warning concerned the AnyIO BlockingPortal alias.
- `npm --prefix frontend run build`: exit 0; production frontend assets generated.
- `node --test tools/chart-math.test.mjs`: exit 0, **4 passed**.
- Offline source-history import experiment: **4 passed**; exact source tree and both commit histories preserved, with rejection of the wrong bundle hash, destination or expected commit.

These are software/publication checks. They do not establish native PostgreSQL concurrency, hosted authentication, a Windows run, vehicle accuracy, a recovered frozen-model binary or a genuine SAN hardware handoff. The earlier clean-install/startup evidence remains separately dated 12 November.

The public repositories were ultimately published through direct browser file commits. The tested automated importer was not installed or used in those repositories; the earlier Git history is retained in downloadable recovery bundles.
