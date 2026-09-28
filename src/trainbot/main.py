"""Entry point for the SNCF Train Telegram Bot."""
from __future__ import annotations

import logging
import sys
from trainbot.bot.service import build_application
from trainbot.config import Config


def main() -> None:
    """Run the SNCF train bot service."""
    config = Config.from_env()

    # Configure logging
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    numeric_level = getattr(logging, config.log_level, logging.INFO)
    logging.basicConfig(level=numeric_level, format=log_format)
    logger = logging.getLogger("trainbot")

    logger.info("Starting SNCF Train Bot...")
    logger.info("Timezone: %s", config.timezone)
    logger.info("Allowed users: %s", list(config.allowed_user_ids))
    logger.info("SNCF API Key configured: %s", "Yes" if config.sncf_api_key else "No (Mock Mode)")

    if not config.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is missing! Please configure it in .env.")
        sys.exit(1)

    try:
        app = build_application(config)
        logger.info("Bot is polling for updates...")
        app.run_polling(drop_pending_updates=True)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot shutting down gracefully.")
    except Exception as exc:
        logger.exception("Fatal error while running bot: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
