## Destination

A fully functional, tested, and containerized Python Telegram bot service deployed in a Proxmox LXC container that delivers scheduled weekday notifications (07:00 Antibes ➔ Nice Ville, 16:00 Nice Ville ➔ Antibes) and on-demand queries for TER train departures, real-time delays, and disruption communications to whitelisted users.

## Notes

- Domain: Commuter train schedules, real-time transit status, Telegram bot API, and Linux LXC service orchestration.
- Key skills: `domain-modeling`, `research`, `prototype`, `tdd`.
- Standing preferences:
  - Python with modern async (`asyncio`, `python-telegram-bot` or lightweight async client).
  - Timezone: `Europe/Paris`.
  - Allowed users restricted strictly by Telegram numeric user ID.
  - Train filter: TER regional trains only.
  - Host environment: Proxmox LXC container with systemd service unit.

## Decisions so far

<!-- the index: one line per closed ticket, enough to judge relevance, then zoom the link for the detail the ticket holds -->

- [SNCF API Research: Departures, Delays, and Disruptions for Antibes ⟷ Nice Ville](file:///home/skiwithuge/workspace/antigravity/trainbot/.scratch/trainbot/issues/01-sncf-api-research.md): Use Navitia `/journeys` with stop areas `87757674` (Antibes) and `87756056` (Nice-Ville) with Basic Auth; filter `commercial_mode == 'TER'` and extract live delay deltas and disruption advisories.
- [Telegram Message Formatting & Interactive UX Prototype](file:///home/skiwithuge/workspace/antigravity/trainbot/.scratch/trainbot/issues/02-telegram-message-formatting.md): Use Telegram HTML mode for robust rendering with strikethrough for delays/cancellations, color emoji badges, and inline refresh/direction-switch buttons.
- [Core Bot Architecture & User ID Whitelisting](file:///home/skiwithuge/workspace/antigravity/trainbot/.scratch/trainbot/issues/03-core-bot-and-auth.md): Built `Config`, `@restricted` decorator rejecting unauthorized IDs with user ID readout, and `/start`, `/help`, `/trains`, `/antibes`, `/nice` handlers.

## Not yet specified

- **API Resiliency & Caching**: How to handle temporary SNCF API outages, network retries, or rate limit throttling gracefully during scheduled broadcast hours.
- **Extended On-Demand Filtering**: Whether to support arbitrary departure time offsets (e.g. `/trains 18:30`) via command arguments.

## Out of scope

- Non-TER trains (TGV INOUI, OUIGO, Intercités) filtered out of departure boards.
- Stations beyond the Antibes ⟷ Nice Ville commuter corridor.
- Public bot access, open user registration, or multi-tenant database.
- Web UI or native mobile application.
