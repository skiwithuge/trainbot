Type: task
Status: resolved
Blocked by: 02, 03

# Scheduler & Automated Commute Broadcasts

## Question

How should the automated notification scheduler be integrated into the Telegram bot event loop to execute reliably at 07:00 and 16:00 Europe/Paris time, only on Monday through Friday, broadcasting the appropriate directional train status to all whitelisted users without blocking or missing runs across container restarts?

## Answer

Implemented in [scheduler.py](file:///home/skiwithuge/workspace/antigravity/trainbot/src/trainbot/scheduler.py) and [service.py](file:///home/skiwithuge/workspace/antigravity/trainbot/src/trainbot/bot/service.py):
1. **Engine**: Integrated with `python-telegram-bot`'s `JobQueue` (backed by `APScheduler`).
2. **Timing & Weekday Filter**:
   - `WEEKDAYS = (1, 2, 3, 4, 5)` (Monday to Friday, mapping to python-telegram-bot 20+ convention where 0 is Sunday).
   - Timezone configured strictly to `Europe/Paris` via `ZoneInfo`.
   - Morning job runs at `07:00` for `CommuteDirection.ANTIBES_TO_NICE`.
   - Evening job runs at `16:00` for `CommuteDirection.NICE_TO_ANTIBES`.
3. **Resilient Broadcast**:
   - Loops through `config.allowed_user_ids` sending the formatted message and interactive buttons.
   - Individual user delivery errors (e.g. user blocked bot or Telegram API rate limits) are caught and logged so other users still receive their notification.
   - Handles network / SNCF API errors during broadcast by sending an informative alert rather than crashing.
4. **Validation**:
   - Verified via [test_scheduler.py](file:///home/skiwithuge/workspace/antigravity/trainbot/tests/test_scheduler.py) asserting job registration and multi-user broadcast delivery.
