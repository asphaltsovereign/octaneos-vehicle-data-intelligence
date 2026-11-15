# SAN-V1 integration gap

The 19 August bench firmware and the recovered OctaneOS importer have different data contracts.

| Field | Bench firmware | OctaneOS workshop importer |
|---|---|---|
| Schema marker | `san_csv_1.0` | `1.0` |
| Vehicle identity | Not emitted | `vehicle_id` required |
| Speed | `gps_speed_kph` | `gps_speed_kmh` |
| Voltage | `voltage_v`, ADC bench voltage | `battery_v`, vehicle battery channel |
| Temperature | `probe_temp_c` | `ambient_temp_c` |
| Position | `latitude_deg` / `longitude_deg` | `gps_lat` / `gps_lon` |
| Time | UTC may be blank without GPS; `uptime_ms` retained | Valid increasing UTC timestamp required |

Check `SAN_REQUIRED` and `_normalize_san` in `backend/app/services/ingestion.py`, plus the stricter workshop checks in `backend/app/workshop/evidence.py`, before writing an adapter. A spelling rename cannot convert an ADC bench voltage into calibrated vehicle-battery voltage, or an unspecified probe temperature into ambient-air temperature. Do not invent `vehicle_id`, GPS time, speed, units or calibration provenance to make an upload pass.

Acceptance for a future adapter: preserve raw bytes/hash; explicit schema/version mapping; documented device/session/vehicle association; supported time basis; declared units; missing-channel handling; calibration identity; a synthetic contract fixture and one genuine bench file. No real SAN-to-OctaneOS integration is claimed in this consolidation.
