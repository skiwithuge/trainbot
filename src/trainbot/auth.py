"""Authentication and authorization middleware for Telegram bot."""
from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Coroutine
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from trainbot.config import Config

logger = logging.getLogger(__name__)


def restricted(
    handler_func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]:
    """Decorator to restrict handler access strictly to allowed user IDs."""

    @functools.wraps(handler_func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        user_id = user.id if user else None
        user_name = user.full_name if user else "Inconnu"
        username = f"@{user.username}" if user and user.username else "sans username"

        config: Config = context.bot_data.get("config")
        if not config:
            config = Config.from_env()

        if not config.is_user_allowed(user_id):
            logger.warning(
                "Unauthorized access attempt blocked: user_id=%s, name=%s, username=%s",
                user_id,
                user_name,
                username,
            )

            # If triggered via button callback
            if update.callback_query:
                await update.callback_query.answer(
                    f"⛔ Accès refusé. Votre ID Telegram ({user_id}) n'est pas autorisé.",
                    show_alert=True,
                )
                return

            # If triggered via text message / slash command
            if update.effective_message:
                denial_msg = (
                    "⛔ <b>Accès non autorisé</b>\n\n"
                    "Ce bot est privé et réservé aux utilisateurs autorisés.\n"
                    f"Votre ID Telegram : <code>{user_id}</code>\n\n"
                    "Transmettez cet identifiant à l'administrateur pour être ajouté à la liste d'accès."
                )
                await update.effective_message.reply_text(
                    denial_msg,
                    parse_mode=ParseMode.HTML,
                )
            return

        return await handler_func(update, context)

    return wrapper
