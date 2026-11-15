# OctaneOS Sentinel V3 Architecture

## Evidence pipeline

1. **Telemetry ingestion**: source contract detection and normalization.
2. **Signal Guardian**: validity, continuity, movement/activity and coverage gates.
3. **Feature Engineering**: derivatives, rolling statistics, acceleration and cross-signal ratios.
4. **ML Anomaly Engine**: unsupervised Isolation Forest. It flags deviation; it does not identify failed hardware.
5. **Engineering Rule Engine**: deterministic domain constraints and operational rules.
6. **Investigation Engine**: converts anomaly + rule evidence into hypotheses.
7. **Evidence Verification**: attaches supporting and contradicting observations.
8. **Safety Agent**: blocks unsupported component claims when required signals are absent.
9. **Health / Risk Scoring**: evidence-weighted screening indicator, not a certified diagnostic score.
10. **Explanation Layer**: UI/report presentation. Optional LLM adapter can be added later without owning the diagnostic decision.

## Why this architecture
The hackathon differentiator is not a chatbot. The core intelligence remains reproducible without an LLM. A generative model can later explain structured evidence, but it must not silently invent faults.
