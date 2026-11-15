# September 8 — 21:00 to 05:00 ML Engineering Block

## 21:00–22:00 — Data acquisition + environment
- install Python dependencies
- download official VED Dynamic Part 1
- extract archive
- confirm weekly CSV files and columns
- run prepared-trip selector for first 60–80 active trips

Gate: `prepared_index.csv` exists and contains multiple VehId values.

## 22:00–23:15 — Dataset audit
- inspect sample counts, speed/RPM coverage, timing gaps and missingness
- reject stationary/low-information trips
- verify no train/validation row leakage
- freeze quality gates

Gate: quality-approved corpus with hashes and vehicle IDs.

## 23:15–00:45 — Baseline training
- create overlapping 16-sample windows, stride 8
- build ~30–50 stable window features
- GroupShuffleSplit by vehicle
- fit RobustScaler + Isolation Forest + PCA + robust deviation model
- calibrate held-out threshold
- save `.joblib` + `model_manifest.json`

Gate: frozen artifact loads successfully and manifest records source hashes/split/feature schema.

## 00:45–02:00 — Validation campaign
- held-out nominal false-positive test
- inject RPM instability, thermal drift, sensor dropout, signal spikes and voltage degradation where signal exists
- compute window-level precision, recall, F1, FPR and detection latency
- tune only from training/reference behavior; never tune on the final held-out results repeatedly

Gate: `validation_report.json` generated with honest claim boundary.

## 02:00–03:00 — Model audit
- inspect weak scenarios and false positives
- test at least 3 random seeds / vehicle splits if corpus is large enough
- compare IF-only vs PCA-only vs ensemble
- check feature coverage and remove unstable/leaky features

Gate: choose one frozen candidate model and record why.

## 03:00–04:00 — Backend integration
- use frozen model for inference rather than fitting on each scored session
- expose model manifest and window anomaly results to frontend
- preserve legacy self-fit detector only as explicit demo/fallback mode

Gate: upload unseen CSV -> frozen Sentinel model -> anomaly windows JSON.

## 04:00–05:00 — Evidence freeze + handoff to visualizer
- run full tests
- save console outputs/screenshots
- record training/validation numbers
- prepare JSON payloads for Model Lab and Anomaly Explorer
- stop ML feature creep at 05:00

Gate: ML core is reproducible enough to build the advanced visualizer on September 9.
