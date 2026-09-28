Type: task
Status: resolved
Blocked by: 01

# Core Bot Architecture & User ID Whitelisting

## Question

How should the Python Telegram bot service be structured to securely enforce numeric user ID access control across commands and callbacks, handle errors cleanly, support environment configuration via `.env`, and provide intuitive `/start`, `/help`, `/trains`, `/antibes`, and `/nice` commands?

## Answer

Implemented the core bot service and access control architecture:
1. **Configuration ([config.py](file:///home/skiwithuge/workspace/antigravity/trainbot/src/trainbot/config.py))**:
   - Loads `.env` with `TELEGRAM_BOT_TOKEN`, `SNCF_API_KEY`, `ALLOWED_USER_IDS`, `TIMEZONE`, and scheduling defaults.
   - Parses `ALLOWED_USER_IDS` into a fast, immutable `frozenset[int]`.
2. **Access Control ([auth.py](file:///home/skiwithuge/workspace/antigravity/trainbot/src/trainbot/auth.py))**:
   - `@restricted` decorator applied to all commands and callback queries.
   - Blocks unauthorized users with security log auditing and returns a polite message displaying their numeric Telegram User ID so they can easily submit it to the bot administrator.
3. **Commands & Callbacks ([handlers.py](file:///home/skiwithuge/workspace/antigravity/trainbot/src/trainbot/bot/handlers.py))**:
   - `/start`: Explains the bot, lists commands, and delivers the initial departure board with interactive buttons.
   - `/help`: Displays command instructions.
   - `/trains`: Smart commute direction auto-detection (before 12:00 -> Antibes ➔ Nice; 12:00 onwards -> Nice ➔ Antibes).
   - `/antibes` & `/nice`: Direct shortcuts for either direction.
   - Inline callbacks: `🔄 Actualiser` (refreshes live times and delays in-place) and `↔️ Inverser` (swaps direction).
4. **Validation ([test_config.py](file:///home/skiwithuge/workspace/antigravity/trainbot/tests/test_config.py), [test_auth.py](file:///home/skiwithuge/workspace/antigravity/trainbot/tests/test_auth.py))**:
   - Comprehensive unit test suite covering whitelist parsing, positive/negative access control, and unauthorized callback alerts.
