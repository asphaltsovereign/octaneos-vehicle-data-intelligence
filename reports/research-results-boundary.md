# Research results: evidence and limits

Source: the preserved `backend/evidence/terminal2_snapshot.json` and September methodology records. No fresh training or held-out model evaluation was run during repository consolidation.

| Historical reported quantity | Value | Interpretation |
|---|---:|---|
| Vehicles: train / calibration / final test | 40 / 9 / 9 | Passenger-car VED research split |
| Feature count | 47 | Frozen V3.2 contract, not every fallback build |
| Controlled perturbation runs detected | 158 / 207 (76.33%) | Synthetic sensitivity |
| Severe perturbation runs detected | 62 / 69 (89.86%) | Synthetic severe-case sensitivity |
| Untouched normal-window false-positive rate | 13.01% | Important weakness, not hidden by detection rate |
| Injected-window precision / recall / F1 | 42.86% / 31.30% / 36.18% | Different denominator from run-level detection |

Expected model SHA-256: `3ee122b87fa5cadfaaa8bd5d5aff44734cddc96cc81cf32e396b6c1e5f692542`. The binary is not present in recovered sources. Do not deserialize an arbitrary similarly named joblib file or present fallback execution as the frozen experiment.

The current software checks verify behavior of the packaged application. They do not reproduce the historical training result, validate a motorcycle fault diagnosis, or establish commercial readiness.

Dataset background: [VED author's repository](https://github.com/gsoh/VED). Original VED data is not redistributed in this consolidation; included examples are synthetic.
