Type: research
Status: resolved
Blocked by:

# SNCF API Research: Departures, Delays, and Disruptions for Antibes ⟷ Nice Ville

## Question

How does the SNCF Open Data / Navitia API structure requests and responses for real-time departures, disruptions, and delays between Antibes and Nice Ville, and how can we reliably filter only TER regional trains while extracting scheduled departure time, estimated/real-time departure time, delay minutes, track/platform (if available), and textual disruption messages?

## Answer

Research completed and documented in [.scratch/trainbot/research/01-sncf-api.md](file:///home/skiwithuge/workspace/antigravity/trainbot/.scratch/trainbot/research/01-sncf-api.md).

Key findings:
1. **Endpoint**: Use `/journeys` with `from=stop_area:SNCF:87757674` (Antibes) and `to=stop_area:SNCF:87756056` (Nice-Ville) or vice-versa with `data_freshness=realtime`.
2. **Auth**: HTTP Basic Auth with API key as username and empty password.
3. **Filtering**: Inspect public transport sections for `commercial_mode == "TER"` and `nb_transfers == 0`.
4. **Delays & Disruptions**: Calculated as the delta between `departure_date_time` (real-time) and `base_departure_date_time` (scheduled). Disruption advisory text parsed from root and journey `disruptions` arrays.
