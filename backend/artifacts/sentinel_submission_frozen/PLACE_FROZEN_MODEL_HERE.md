# Frozen model slot

Before the final demo or deployment, copy these three files from the frozen model
directory on the training machine into this directory:

- `sentinel_baseline.joblib`
- `model_manifest.json`
- `final_test_report.json`

The expected model is `sentinel-powertrain-baseline-0.5` and the expected SHA-256
for `sentinel_baseline.joblib` is:

`3ee122b87fa5cadfaaa8bd5d5aff44734cddc96cc81cf32e396b6c1e5f692542`

Sentinel verifies the manifest checksum before deserializing the model. A missing,
unreadable, or mismatched artifact activates a clearly labelled local fallback.
