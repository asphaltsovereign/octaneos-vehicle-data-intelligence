# OctaneOS Sentinel runtime evidence fix

This overlay does **not** retrain or modify the frozen V3.2 model artifact.

It fixes two runtime presentation/evidence issues:

1. `/model/info` now reads the nested V3.2 validation report correctly instead of returning null metrics.
2. Dominant anomaly contributors are filtered to the frozen model's declared capability signals. Sparse `battery__coverage`, `temp__coverage`, etc. can no longer create unsupported voltage/thermal hypotheses in the public powertrain model.

After overlay, rerun pytest and restart Uvicorn.
