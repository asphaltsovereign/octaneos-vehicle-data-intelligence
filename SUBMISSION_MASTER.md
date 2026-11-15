# OctaneOS Sentinel — submission master

## Deadline and required bundle

The live Unstop listing for **Innovation Hacks Global AI Hackathon 2026** shows the
Project Submission round ending **10 September 2026 at 11:23 PM IST**. The supplied
screenshots and listing require:

- project title and description
- GitHub repository
- PPT or PDF presentation
- demo video of 3–5 minutes
- source code and README
- deployment link if available
- screenshots optional

The judging criteria are innovation and creativity, technical excellence, real-world
impact, scalability, user experience, and presentation quality.

## Reminder audit

Two opportunities appear in the connected mail account and must not be mixed:

- Innovation Hacks Global AI Hackathon 2026: registration confirmation on 28 August and
  a 1 September organizer update encouraging teams to explore Breeth AI memory.
- StartupX Hackathon 2026: Unstop sent an **Incomplete Submission Notification** on
  5 September for “Round 1: Startup Idea & PPT Submission.” That reminder concerns a
  separate event.

## Submission title

**OctaneOS Sentinel: Evidence-First AI for Vehicle Telemetry**

## One-line pitch

An explainable, local-first AI workstation that converts vehicle telemetry into bounded
anomaly evidence, inspection steps, and claim-safe reports.

## Paste-ready project description

OctaneOS Sentinel helps engineers screen vehicle telemetry without turning a statistical
anomaly into an unsupported diagnosis. A quality gate first checks whether an uploaded
CSV is suitable for analysis. The validated architecture uses a checksum-locked multivariate
ensemble across synchronized behavioural windows. If that binary is not packaged, the live
application explicitly switches to a labelled local fallback rather than claiming frozen-model
execution. Deterministic automotive rules convert deviations
into testable hypotheses, retain contradictions, and recommend inspection steps. A
safety layer blocks claims about ECU codes, AFR, injector condition, ignition timing,
ethanol content, remaining useful life, and vehicle-specific health when the required
signals or validation do not exist.

The hackathon build includes a six-screen React workstation, FastAPI analysis service,
controlled fault-injection lab, model card, provenance and SHA-256 evidence, CSV import,
downloadable reports, and an optional language-model explanation layer. Core analysis
runs locally; raw telemetry is excluded from cloud prompts and an instant deterministic
fallback keeps the workflow operational offline.

The frozen public passenger-car baseline used 40 training vehicles, 9 calibration
vehicles, and 9 untouched test vehicles. It detected 158 of 207 supported controlled
perturbation runs (76.33%) and 62 of 69 severe runs (89.86%). The untouched normal-window
false-positive rate was 13.01% and injected-window F1 was 36.18%. These figures measure
screening sensitivity under controlled perturbations, not component-diagnosis accuracy.
The locked product path connects passive SAN-V1 motorcycle acquisition to vehicle-specific
validation before any Yamaha R15 health claim.

## Suggested tags

Applied AI, Machine Learning, Explainable AI, Agentic Workflow, Automotive Telemetry,
Edge AI, Predictive Screening, Safety-Critical AI

## Terminal 2 engineering audit

### Verified evidence

| Item | Result |
|---|---:|
| Frozen model | `sentinel-powertrain-baseline-0.5` |
| Model SHA-256 | `3ee122b87fa5cadfaaa8bd5d5aff44734cddc96cc81cf32e396b6c1e5f692542` |
| Window features | 47 |
| Capability signals | speed, rpm, MAF, engine load |
| Vehicle split | 40 train / 9 calibration / 9 final test |
| Decision threshold | 0.4241655642 |
| Ensemble weights | IF 0.10 / PCA 0.70 / Robust-Z 0.20 |
| Untouched normal-window FPR | 13.01% |
| Controlled injection window F1 | 36.18% |
| Controlled injection run detection | 158/207 = 76.33% |
| Severe run detection | 62/69 = 89.86% |
| Terminal test gate | 20 passed, 1 dependency warning |
| Current polished regression gate | 39 passed |

### What failed and what changed

The first failed test still expected battery evidence from a model that does not declare
battery capability. Updating that test to RPM instability was the correct engineering
decision. An accidental edit then removed the test client imports, producing a NameError;
the imports were restored and all 20 tests passed. The cloud explainer later failed first
with a timeout and then an AttributeError while parsing provider content. The release
parser now accepts string content, multipart text content, and reasoning text; every
provider failure returns a structured local fallback. A 35-second ceiling and an
explicit Instant Local mode protect the recorded demo.

### Claims to avoid

- Do not say “90% accurate.” Say “89.86% severe controlled-run detection.”
- Do not present 76.33% run detection as diagnosis accuracy.
- Do not claim thermal or voltage validation; those scenarios were skipped because the
  frozen model lacks the required signals.
- Do not claim Yamaha R15 V2 health validation from public VED passenger-car data.
- Do not claim ECU/DTC, AFR, injector, ignition, fuel-pump, ethanol, or RUL evidence.

## Hackathon pattern and build decision

The event rewards a short proof loop more than feature count: a clear real-world problem,
a visible working product, technical evidence, measurable impact, honest scalability,
and a crisp presentation. The strongest demo sequence is therefore:

1. Establish a normal reference.
2. Apply a severe RPM perturbation with the label hidden from the model.
3. Show detection overlap and synchronized telemetry.
4. Open the evidence graph and blocked claims.
5. Show the frozen model split, checksum, and honest metrics.
6. Finish on the locked SAN-V1 integration path.

Adding a late sponsor SDK or retraining the frozen model would weaken reproducibility.
Keep Breeth as a future evidence-summary memory adapter, not a submission dependency.

## Final execution order

1. Merge the release ZIP over the existing Windows project so the local frozen artifact
   remains in `backend/artifacts/sentinel_submission_frozen/`.
2. Run `VERIFY_SUBMISSION_WINDOWS.ps1`. Do not record until the checksum gate passes.
3. Run `START_OCTANEOS_WINDOWS.bat` and execute the exact flow in `docs/DEMO_SCRIPT.md`.
4. Record and upload the 3–5 minute video.
5. Create or update the GitHub repository, including the frozen submission artifact or a
   release download with the exact checksum.
6. Deploy the Docker service if time permits. A local demo is safer than a broken link.
7. Paste the description above, add the GitHub/video/deployment links, upload the deck,
   and submit before the deadline.

## Only manual blocker in this package

The uploaded ZIPs did not contain `sentinel_baseline.joblib`, `model_manifest.json`, or
`final_test_report.json`. Terminal 2 proves they exist on the Windows machine. Copy those
exact files into the frozen model slot before recording or deployment. The software will
run without them, but it will correctly display **LABELLED FALLBACK** rather than claiming
the frozen model is active.
