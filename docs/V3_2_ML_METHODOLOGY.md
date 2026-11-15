# Sentinel V3.2 ML Methodology Lock

## Why V3.2 exists
Candidate 0.4 proved the full training pipeline but failed anomaly-sensitivity validation. V3.2 corrects the methodology before UI/API freeze.

## Partition policy
Vehicles, not telemetry rows, are the unit of isolation:

- Training vehicles: fit RobustScaler, Isolation Forest, PCA and robust reference statistics.
- Calibration vehicles: choose ensemble weights, detector thresholds and final decision threshold using untouched normal windows plus controlled medium/severe perturbations.
- Final-test vehicles: never used for fitting, score normalization, weight selection or threshold calibration.

No vehicle may occur in more than one partition.

## Feature-selection policy
Feature survival is decided from the training partition only. Calibration/test windows do not determine feature availability.

## Capability policy
A signal is a model capability only if dynamic features for that signal survive training. A mere `<signal>__coverage` feature does not make the model capable of diagnosing that signal. This prevents sparse OAT/HV channels from activating unsupported thermal/electrical tests.

## Controlled perturbation policy
Scenarios are evaluated at mild, medium and severe levels. The injected scenario/severity remain ground truth in the validation harness only; they are never passed to the anomaly model as labels.

A feature window is treated as fault-positive only when at least 50% of that window overlaps the injected sample interval.

## Metrics
Report separately:

- untouched final-test normal false-positive rate;
- controlled-injection window precision/recall/F1;
- controlled-injection run-level detection rate;
- mild/medium/severe sensitivity;
- individual detector final-test FPR and injected-window recall;
- median detection latency.

Do not call controlled-injection results real-world failure-prediction accuracy.

## Claim boundary
VED validates the public passenger-car telemetry methodology. It is not Yamaha R15, SAN-V1, ethanol, component-failure, or remaining-useful-life evidence.
