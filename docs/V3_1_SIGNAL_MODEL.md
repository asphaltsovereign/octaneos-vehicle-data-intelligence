# Sentinel V3.1 Signal Model

Primary public VED powertrain baseline: speed + RPM + MAF and/or absolute engine load.
OAT, fuel-rate, and HV battery fields are optional capability channels and are not imputed as if universally present.
The model preparation gate requires strong RPM coverage and at least one load-context signal (MAF or engine load).
Prepared corpora are capped per vehicle to reduce dominance and preserve vehicle-level holdout credibility.
