# 0001. SNCF Open Data API vs SNCF Voyageurs CMS Boundaries

## Context

During testing on the Antibes ⟷ Nice-Ville corridor, a passenger noticed that the customer-facing website `sncf-voyageurs.com` displayed an onboard comfort advisory on train 86087 ("TOILETTES HORS SERVICE"), while the official `api.sncf.com` response did not return this message, despite returning operational traffic alerts (e.g. "Défaillance de matériel" on train 86083).

Investigation revealed that:
1. `api.sncf.com` is the official Navitia-powered SNCF Open Data circulation API. It syndicates real-time train movement, departure times, minute-level delays, platform/track changes, cancellations, and operational traffic incidents (safety, line works, signaling, rolling stock breakdown).
2. Onboard rolling stock comfort notes (such as broken toilets, catering notices, or coach-specific amenities) are entered into SNCF Voyageurs' private customer-facing CMS/BFF (`api.voyageurs.sncf.com` / `sncf-voyageurs.com`) and are not propagated into the public Open Data API feed.
3. Scraping `sncf-voyageurs.com` would introduce severe fragility, bot-protection roadblocks (Cloudflare 403), and high risk of breakage.

## Decision

We rely strictly on the official SNCF Open Data / Navitia API (`api.sncf.com/v1/coverage/sncf/journeys`) as the single source of truth for circulation, live departures, delay calculations, cancellations, and official operational alerts.

We do not scrape or proxy `sncf-voyageurs.com` for onboard comfort notices. Train-specific operational alerts published in the API (matching `impacted_objects` or `vehicle_journey` IDs) are displayed directly under the affected train card, and general corridor disruptions are displayed at the bottom under "Infos Trafic".

## Consequences

- The bot remains reliable, lightweight, and compliant with official SNCF Open Data terms of service.
- If SNCF publishes rolling stock or traffic disruptions in the Open Data feed, the bot displays them immediately.
- Minor onboard comfort advisories exclusive to the commercial website will not appear in the bot.
