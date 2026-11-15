# OctaneOS Sentinel V3.4 — final 3-minute hackathon demo

Record at 1920×1080 if practical and use **Instant Local** for the explanation step so the live demo does not depend on cloud latency.

## 0:00–0:25 — Problem

**Say:** “Vehicle telemetry tools can turn an unusual signal into an overconfident diagnosis. OctaneOS Sentinel separates anomaly screening, engineering evidence, and diagnostic claims.”

Show **Command Center** and the two truth badges. Explicitly point out **SYNTHETIC DEMO TELEMETRY**. If the exact frozen artifact was restored, the second badge says **CHECKSUMMED FROZEN RUNTIME**; otherwise it says **LABELLED LOCAL FALLBACK**. Describe only the runtime actually shown.

## 0:25–0:55 — Engineering timeline

Point to the four synchronized lanes: **RPM (rev/min)**, **Speed (km/h)**, **Engine load (%)**, and **Anomaly score (0–1)**.

**Say:** “The chart uses physical units and a shared timebase. The built-in session is synthetic validation data, not motorcycle-measured evidence.”

## 0:55–1:35 — Controlled perturbation

Open **Fault Lab**, choose **RPM instability → Medium**, then **Generate + Analyze**.

**Say:** “We inject a known RPM disturbance, but the scenario label is kept outside the screening input. The amber band is ground truth for evaluation; detected anomaly regions are overlaid independently.”

Point to the ground-truth interval and detection-overlap result. If the run misses, say it is an honest miss rather than hiding it.

## 1:35–2:15 — Investigation and safety

Open **Investigation**, then select **Instant Local**.

**Say:** “An anomaly does not automatically become a component diagnosis. Sentinel retains supporting evidence and contradictions, proposes inspection steps, and blocks claims the available signals cannot support.”

Show the blocked-claims/safety section and deterministic explanation.

## 2:15–2:45 — Model governance

Open **Model Card**.

If the exact frozen artifact is active, show its checksum and validation metrics and say: “These are screening-sensitivity metrics under controlled perturbations, not component-diagnosis accuracy.”

If the runtime is fallback, say: “This deployment does not contain the frozen binary, so Sentinel exposes that fact and uses a labelled local fallback instead of pretending the validated model is executing.” Do not quote frozen-runtime metrics as live execution results.

## 2:45–3:10 — Close

Open **Submission Proof**.

**Say:** “The product path is telemetry → quality gate → screening → engineering rules → safety gate → explanation. The next validation step is passive SAN-V1 motorcycle acquisition and vehicle-specific testing before any Yamaha R15 health claim. Evidence first. AI second.”

## Judge-safe wording

Prefer **screening**, **anomaly evidence**, **controlled perturbation**, **bounded hypothesis**, **inspection recommendation**, and **validation evidence**. Do not claim component diagnosis accuracy, remaining useful life, ECU control, AFR/ethanol sensing, or Yamaha R15 health unless the corresponding measured and validated evidence exists.
