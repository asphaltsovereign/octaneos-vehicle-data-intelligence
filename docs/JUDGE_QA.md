# Judge Q&A

## What exactly is new here?

Sentinel separates anomaly detection, engineering hypotheses, contradictions, claim
blocking, and language explanation into inspectable stages. Most demos collapse those
steps into one confident diagnosis. This build makes uncertainty and capability limits
part of the product.

## Does it diagnose a failed motorcycle component?

No. It screens for behavioural deviation and recommends verification steps. The public
VED baseline does not validate Yamaha R15 V2 component health. Vehicle-specific claims
remain gated until SAN-V1 longitudinal data and independent labels exist.

## What data trained the model?

Public passenger-car telemetry prepared into isolated trips. The split used 40 training
vehicles, 9 calibration vehicles, and 9 untouched test vehicles. No final-test vehicle
participated in fitting or threshold selection.

## Is 76.33% accuracy?

No. It is run-level detection sensitivity over 207 supported controlled perturbation
experiments. Window precision was 42.86%, recall 31.30%, and F1 36.18%. Untouched
normal-window false-positive rate was 13.01%.

## Why is the false-positive rate important?

A screening product must expose it because false alerts create inspection cost. The
current result is a research baseline, not a production diagnostic threshold. More
diverse clean telemetry and vehicle-specific calibration are the next validation step.

## Why call the workflow agentic?

Specialized bounded roles own different decisions: source validation, signal quality,
anomaly screening, evidence testing, claim safety, and explanation. The roles pass
structured evidence. They cannot invent sensors or override capability gates.

## What happens without internet or an LLM key?

Telemetry ingestion, feature engineering, anomaly scoring, rules, safety checks, charts,
and reports remain local. The instant deterministic explanation remains available. Raw
telemetry never enters the optional language-model request.

## How do you protect the frozen model?

The manifest declares the artifact SHA-256. The runtime computes the checksum before
joblib deserialization. A mismatch blocks the artifact and activates a labelled fallback.

## How does it scale beyond one vehicle?

The CSV/SAN-V1 contract stays stable while capability-specific models change behind it.
Each model declares supported signals and domain boundaries. The same investigation UI
can serve fleet, workshop, and research workflows without pretending one baseline fits
every vehicle.

## Why did you not add Breeth after the organizer update?

The update encouraged exploration but did not make it a submission requirement. The
architecture was already frozen and the deadline was close. Adding external memory at
the last moment would increase failure and privacy risk. A future adapter could persist
approved evidence summaries while raw telemetry remains local.

## What would you validate next?

Collect longitudinal TV-001/TV-002 telemetry through passive SAN-V1 hardware, establish
independent inspection labels, train a vehicle-specific baseline, run prospective tests,
and publish false-positive and missed-detection results by operating condition.
