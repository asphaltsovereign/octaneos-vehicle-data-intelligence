# Sentinel ML V3.3 — Session-Robust Calibration

V3.3 addresses the V3.2 development-audit result where pooled calibration achieved ~5% normal FPR but the vehicle-held-out audit rose to ~13%.

Changes:
- New deterministic vehicle lockbox seed for V3.3.
- Per-session normal-score envelopes instead of pooled-window-only calibration.
- Conservative 90th-percentile guard across calibration sessions.
- Default calibration normal-FPR target reduced to 2%.
- Ensemble calibration optimizes injected-run detection plus window sensitivity under FPR constraints.
- Weight grid may suppress a detector to zero when it harms calibration, while keeping at least two active detectors.
- Final-test metrics remain separated from calibration metrics.

Claim boundary: controlled perturbation results are anomaly-sensitivity evidence, not real-world component-failure diagnostic accuracy or RUL prediction.
