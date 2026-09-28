"""Application factory and initialization for Telegram bot."""
from __future__ import annotations

import logging
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from trainbot.bot.handlers import (
    antibes_command,
    callback_handler,
    help_command,
    nice_command,
    start_command,
    trains_command,
)
from trainbot.config import Config
from trainbot.sncf.client import SncfClient

logger = logging.getLogger(__name__)


def build_application(config: Config) -> Application:
    """Build and configure the Telegram application."""
    if not config.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN must be set in configuration or environment.")

    # Initialize SNCF client (using mock mode if API key is not yet provided)
    sncf_client = SncfClient(
        api_key=config.sncf_api_key,
        timezone=config.timezone,
        mock_mode=not bool(config.sncf_api_key),
    )

    app = Application.builder().token(config.telegram_bot_token).build()

    # Store shared objects in bot_data
    app.bot_data["config"] = config
    app.bot_data["sncf_client"] = sncf_client

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("trains", trains_command))
    app.add_handler(CommandHandler("antibes", antibes_command))
    app.add_handler(CommandHandler("nice", nice_command))

    # Register callback query handler for inline buttons
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("Application initialized with %d allowed users.", len(config.allowed_user_ids))
    return app
