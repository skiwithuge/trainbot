# Research Findings: SNCF API Integration for Antibes ⟷ Nice Ville

**Date**: 2026-09-28
**Topic**: SNCF Open Data / Navitia API structure for real-time TER departures, delays, and disruptions.
**Primary Sources**:
- Navitia API Documentation: `https://doc.navitia.io/`
- SNCF API Endpoint: `https://api.sncf.com/v1/coverage/sncf/`
- SNCF Open Data: `https://ressources.data.sncf.com/`

---

## 1. Authentication & Base URL
- **Base URL**: `https://api.sncf.com/v1/coverage/sncf`
- **Authentication**: HTTP Basic Auth with the API Key as username and an empty password:
  ```python
  import httpx
  auth = httpx.BasicAuth(username=SNCF_API_KEY, password="")
  # Or via header: "Authorization": SNCF_API_KEY
  ```

## 2. Station Identification (Stop Areas & UIC Codes)
- **Antibes Station**:
  - UIC Code: `87757674`
  - Stop Area ID: `stop_area:SNCF:87757674`
- **Nice-Ville Station**:
  - UIC Code: `87756056`
  - Stop Area ID: `stop_area:SNCF:87756056`
- **Dynamic Resolution Fallback**:
  - `GET /places?q=Antibes` and `GET /places?q=Nice+Ville` can dynamically verify or resolve stop areas if the ID format ever shifts between Navitia coverage datasets.

## 3. Recommended Endpoint: `/journeys` vs `/departures`

### Why `/journeys` is optimal for Point-to-Point Commutes:
Calling `/stop_areas/{origin_id}/departures` returns all departures in all directions (e.g. towards Cannes, Grasse, Marseille, Les Arcs). Filtering whether a departure actually stops at Nice Ville requires fetching vehicle journey stop lists.

Instead, `/journeys` directly computes the transit between Antibes and Nice Ville:
```http
GET /v1/coverage/sncf/journeys?from=stop_area:SNCF:87757674&to=stop_area:SNCF:87756056&datetime=YYYYMMDDTHHMMSS&data_freshness=realtime&min_nb_journeys=5
```

### Key Request Parameters:
- `from`: Origin stop area ID (`stop_area:SNCF:87757674` or `stop_area:SNCF:87756056`)
- `to`: Destination stop area ID
- `datetime`: ISO-like string `YYYYMMDDTHHMMSS` (local Paris time)
- `data_freshness`: `realtime` (ensures live delays and disruptions are reflected)
- `min_nb_journeys`: `5` (to ensure we have at least 3-4 upcoming direct trains after filtering)

## 4. Response Parsing & TER Filtering

### Extracting TER services:
Within the journey JSON, inspect `sections` where `type == "public_transport"`:
```json
{
  "display_informations": {
    "commercial_mode": "TER",
    "network": "TER",
    "code": "86043",
    "direction": "Ventimiglia (Italie)",
    "headsign": "86043"
  }
}
```
- **Filter**: Only include journeys where `commercial_mode == "TER"` (or `network == "TER"`). Exclude journeys where `commercial_mode` is `TGV INOUI` or `OUIGO`.
- **Direct Filter**: Check that transfers count is 0 (`journey["nb_transfers"] == 0`).

### Calculating Delays:
- Scheduled departure: `base_departure_date_time` (e.g. `20260928T071500`)
- Real-time departure: `departure_date_time` (e.g. `20260928T072500`)
- **Delay in minutes**: Difference between real-time and scheduled timestamp.
  - If `delay == 0`: On time (`A l'heure`)
  - If `delay > 0`: Delayed by X minutes (`+X min`)
  - If `journey["status"] == "NO_SERVICE"` or disruption indicates cancellation: `Supprimé` (Cancelled).

### Extracting Disruptions & Messages:
- Root-level `disruptions` array or journey-level `disruptions`:
  ```json
  {
    "id": "...",
    "status": "active",
    "severity": { "name": "SIGNIFICANT_DELAYS", "effect": "SIGNIFICANT_DELAYS" },
    "messages": [
      {
        "text": "Incident sur la voie entre Cannes et Antibes. Retards de 15 à 30 minutes.",
        "channel": { "name": "moteur" }
      }
    ]
  }
  ```
- Collect distinct messages that affect the active commuter route and append them to the notification summary.

## 5. Fallback & Mock Fixture Design
For unit tests, dry-runs, and offline CI without an active network connection, a mock JSON fixture simulating normal, delayed, and cancelled TER trains between Antibes and Nice Ville will be provided.
