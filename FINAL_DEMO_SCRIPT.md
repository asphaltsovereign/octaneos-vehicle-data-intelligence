# OctaneOS Sentinel V3.4 — 90-second live demo script

## Before recording

1. Open `/health` and confirm `status: ok` and `frontend_built: true`.
2. Open Command Center and confirm the runtime badge says either **CHECKSUMMED FROZEN RUNTIME** (verified artifact present) or **LABELLED LOCAL FALLBACK** (artifact absent).
3. Never describe synthetic demo data as motorcycle-measured data.

## Demo flow

**0–15 s — Problem**

“Vehicle telemetry tools often jump from an unusual signal directly to a diagnosis. OctaneOS Sentinel separates screening evidence from diagnostic claims.”

**15–35 s — Reference run**

Show **Command Center**. Point to the **SYNTHETIC DEMO TELEMETRY** label, data-quality score and the four physical-unit lanes: RPM, speed, engine load and anomaly score.

**35–60 s — Controlled disturbance**

Open **Fault Lab**, choose **RPM instability / Medium**, then **Generate + Analyze**. Point to the amber **CONTROLLED FAULT INJECTION** interval and the independently detected anomaly regions. Explain that the injected label is kept outside screening and used only for evaluation.

**60–78 s — Investigation**

Open **Investigation**. Show supporting evidence, contradictions, recommended inspection steps and blocked claims. Run **Instant Local** so the explanation path stays deterministic and does not depend on cloud latency.

**78–90 s — Close**

“OctaneOS is evidence-first: telemetry enters a quality gate, screening finds unusual behaviour, engineering rules test hypotheses, and the safety layer blocks unsupported claims. The next product step is SAN-V1 vehicle acquisition and vehicle-specific validation.”

## Judge-safe wording

Say **screening**, **anomaly evidence**, **controlled perturbation**, **bounded hypothesis**, and **inspection recommendation**. Do not claim component diagnosis accuracy, remaining useful life, ECU control, ethanol sensing, or Yamaha R15 health unless corresponding measured/validated evidence actually exists.
