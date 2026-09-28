"""Telegram command and callback handlers."""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from trainbot.auth import restricted
from trainbot.bot.formatter import format_commute_message, make_commute_keyboard
from trainbot.config import Config
from trainbot.sncf.client import SncfClient
from trainbot.sncf.models import CommuteDirection

logger = logging.getLogger(__name__)


def get_default_direction(timezone_str: str) -> CommuteDirection:
    """Infer likely commute direction based on current time (morning vs evening)."""
    tz = ZoneInfo(timezone_str)
    now = datetime.now(tz)
    # Before 12:00: Antibes -> Nice, 12:00 onwards: Nice -> Antibes
    if now.hour < 12:
        return CommuteDirection.ANTIBES_TO_NICE
    return CommuteDirection.NICE_TO_ANTIBES


@restricted
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    config: Config = context.bot_data["config"]
    direction = get_default_direction(config.timezone)

    welcome_text = (
        "👋 <b>Bonjour !</b>\n\n"
        "Je suis votre assistant TER direct <b>Antibes ⟷ Nice-Ville</b>.\n"
        "Je vous préviens des prochains départs, retards et perturbations.\n\n"
        "📅 <b>Alertes automatiques :</b>\n"
        "• 07:00 (Semaine) : Antibes ➔ Nice-Ville\n"
        "• 16:00 (Semaine) : Nice-Ville ➔ Antibes\n\n"
        "⚡ <b>Commandes disponibles :</b>\n"
        "• /trains : Prochains trains selon le moment de la journée\n"
        "• /antibes : Départs depuis Antibes vers Nice\n"
        "• /nice : Départs depuis Nice vers Antibes\n"
        "• /help : Afficher l'aide\n\n"
        "<i>Chargement des prochains trains en cours...</i>"
    )

    msg = await update.effective_message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

    client: SncfClient = context.bot_data["sncf_client"]
    try:
        status = await client.get_next_trains(direction, count=config.max_departures)
        text = format_commute_message(status)
        keyboard = make_commute_keyboard(direction)
        await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception as exc:
        logger.error("Failed to fetch trains on /start: %s", exc)
        await msg.edit_text(
            f"{welcome_text}\n\n⚠️ <i>Impossible d'obtenir les horaires en direct ({exc}).</i>",
            parse_mode=ParseMode.HTML,
        )


@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "ℹ️ <b>Aide - Bot TER Antibes ⟷ Nice</b>\n\n"
        "<b>Commandes :</b>\n"
        "• /trains : Prochains trains selon l'heure (Antibes le matin, Nice l'après-midi)\n"
        "• /antibes : Prochains TER au départ d'Antibes vers Nice-Ville\n"
        "• /nice : Prochains TER au départ de Nice-Ville vers Antibes\n"
        "• /help : Affiche ce message d'aide\n\n"
        "<b>Boutons interactifs :</b>\n"
        "• 🔄 <b>Actualiser</b> : Rafraîchit les horaires et retards en temps réel\n"
        "• ↔️ <b>Inverser</b> : Bascule instantanément sur l'autre sens de trajet"
    )
    await update.effective_message.reply_text(help_text, parse_mode=ParseMode.HTML)


@restricted
async def trains_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /trains command with smart directional inference."""
    config: Config = context.bot_data["config"]
    direction = get_default_direction(config.timezone)
    await _send_departures(update, context, direction)


@restricted
async def antibes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /antibes (Antibes -> Nice-Ville)."""
    await _send_departures(update, context, CommuteDirection.ANTIBES_TO_NICE)


@restricted
async def nice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /nice (Nice-Ville -> Antibes)."""
    await _send_departures(update, context, CommuteDirection.NICE_TO_ANTIBES)


async def _send_departures(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    direction: CommuteDirection,
) -> None:
    """Helper to query SNCF API and reply with formatted departures."""
    config: Config = context.bot_data["config"]
    client: SncfClient = context.bot_data["sncf_client"]

    waiting_msg = await update.effective_message.reply_text(
        f"🔍 Recherche des prochains TER <b>{direction.origin_name} ➔ {direction.destination_name}</b>...",
        parse_mode=ParseMode.HTML,
    )

    try:
        status = await client.get_next_trains(direction, count=config.max_departures)
        text = format_commute_message(status)
        keyboard = make_commute_keyboard(direction)
        await waiting_msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception as exc:
        logger.error("Error fetching departures for %s: %s", direction, exc)
        await waiting_msg.edit_text(
            f"❌ <b>Erreur :</b> Impossible de récupérer les départs ({exc}).",
            parse_mode=ParseMode.HTML,
        )


@restricted
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button clicks (refresh and switch direction)."""
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    config: Config = context.bot_data["config"]
    client: SncfClient = context.bot_data["sncf_client"]

    if ":" not in data:
        await query.answer()
        return

    action, dir_str = data.split(":", 1)
    try:
        direction = CommuteDirection(dir_str)
    except ValueError:
        await query.answer("Sens inconnu.")
        return

    # Acknowledge the callback immediately so user sees responsiveness
    await query.answer("Actualisation...")

    try:
        status = await client.get_next_trains(direction, count=config.max_departures)
        text = format_commute_message(status)
        keyboard = make_commute_keyboard(direction)

        # Only edit if content actually changed to avoid telegram "message is not modified" error
        if query.message and query.message.text_html != text:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception as exc:
        logger.error("Error updating callback query %s: %s", data, exc)
        await query.answer(f"Erreur d'actualisation : {exc}", show_alert=True)
