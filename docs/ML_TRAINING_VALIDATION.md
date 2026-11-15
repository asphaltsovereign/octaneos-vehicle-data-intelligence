# OctaneOS Sentinel V3 — ML Training & Validation Protocol

## Core rule
Sentinel must not fit an anomaly model on the same session it is scoring in production. A baseline model is trained on quality-approved reference sessions, frozen, versioned, and then used for inference on unseen sessions.

## Hackathon baseline domain
Primary dataset: Vehicle Energy Dataset (VED), public passenger-car OBD-II telemetry. It is used to validate telemetry-learning and anomaly-detection methodology only. It is not Yamaha R15 V2 evidence and does not establish component-failure prediction accuracy.

## Data split
Split by vehicle ID whenever the dataset contains multiple vehicles. This prevents windows from the same vehicle appearing in both training and validation. If only one vehicle is available, split by whole session/trip, never by randomly shuffled rows.

## Training unit
- 16 samples per window
- 8-sample stride (50% overlap)
- fixed feature schema built from speed, RPM, temperature, fuel rate, voltage/SOC when available, cross-signal correlations, dynamics, missingness and timing quality

## Model
- RobustScaler
- Isolation Forest
- PCA reconstruction error
- robust multivariate deviation
- calibrated ensemble score
- threshold calibrated against held-out nominal/reference windows

## Validation
1. Held-out public reference trips: estimate false-positive rate.
2. Controlled fault injection on held-out trips: estimate sensitivity/detection recall, precision, F1 and detection latency.
3. Report every synthetic result as controlled-injection validation, not real component-failure accuracy.
4. Later: replace public baseline with SAN-V1 / TV-001 longitudinal baselines and validate against physical measurements.

## Reproducibility
Every frozen model writes:
- model_manifest.json
- model artifact SHA-256
- source hashes
- feature list
- training/validation vehicle and session counts
- window size/stride
- threshold
- held-out normal false-positive rate
- model version

## Commands
1. Download VED Part 1 using `backend/scripts/download_ved.ps1`.
2. Extract the archive with 7-Zip.
3. `python scripts/prepare_ved.py --input-dir data/raw_ved --output-dir data/prepared_ved --max-trips 80`
4. `python scripts/train_ved.py --prepared-dir data/prepared_ved --output-dir artifacts/sentinel_baseline`
5. `python scripts/validate_ved.py --prepared-dir data/prepared_ved --model-dir artifacts/sentinel_baseline`
6. Run `python -m pytest -q` before accepting the model.
