# Sentinel Dataset Strategy — Hackathon + Startup

## Primary training source: VED
Use the official Vehicle Energy Dataset (VED) from the University of Michigan / gsoh public repository. It contains real-world OBD-II time-series data from 383 personal cars, including 264 gasoline vehicles, with fields such as speed, engine RPM, MAF, load, ambient temperature, fuel rate, battery/energy signals and GPS.

Sentinel uses VED for **public passenger-car telemetry baseline learning and software/ML validation only**. It must never be described as Yamaha R15 V2 evidence or real component-failure ground truth.

### Tonight's scope
Download **VED Dynamic Data Part 1 only** first. Do not waste the first engineering block downloading every possible dataset. Extract it, select 60–80 quality-approved active trips, then train the baseline model.

### Why VED is primary
- real-world, naturalistic OBD-II telemetry
- many vehicles and trips
- enough diversity for train/held-out vehicle splits
- automotive variables relevant to OctaneOS
- Apache-2.0 licensed source repository
- already compatible with the OctaneOS VED adapter

## Secondary external benchmark: FordA / FordB
FordA and FordB are public automotive time-series classification datasets derived from engine-noise measurements with binary symptom labels. Use them only as an **external automotive ML benchmark**, not as the primary Sentinel telemetry model, because their signals are anonymized/univariate and do not match the OctaneOS telemetry schema.

Potential use after the core VED pipeline is complete:
- train a separate 1D classifier or anomaly benchmark
- demonstrate that the ML subsystem can be evaluated on labeled automotive symptom data
- keep the result separate from VED/SAN-V1 health claims

## Not core tonight
- eVED: useful later for richer road/geospatial context; not needed for the first Sentinel baseline.
- CAN intrusion datasets: valuable for a future cybersecurity module, but they measure network attacks rather than mechanical/energy health.
- synthetic 'engine failure' Kaggle datasets: do not use as flagship evidence when stronger real automotive sources are available.
- NASA C-MAPSS / industrial predictive-maintenance data: good methodology references, wrong domain for the core automotive claim.

## Leakage prevention
Do not randomly split rows. Split by **vehicle_id** where possible so an unseen vehicle is held out. Otherwise split by entire trip/session. Overlapping windows from one trip must never land in both training and validation.

## Validation layers
1. Held-out VED reference trips -> normal false-positive rate.
2. Controlled fault injection into held-out trips -> anomaly sensitivity/recall, precision, F1, latency.
3. FordA/FordB later -> separate labeled automotive benchmark.
4. SAN-V1 bench and TV-001 longitudinal data later -> real startup validation.
