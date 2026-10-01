"""Telegram command and callback handlers."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from trainbot.auth import restricted
from trainbot.bot.formatter import (
    format_bus_message,
    format_commute_message,
    make_bus_keyboard,
    make_commute_keyboard,
)
from trainbot.config import Config
from trainbot.envibus.client import EnvibusClient, get_itinerary_url
from trainbot.envibus.models import BusCommuteStatus
from trainbot.sncf.client import SncfClient
from trainbot.sncf.models import CommuteDirection, CommuteStatus

logger = logging.getLogger(__name__)

DEFAULT_BUS_COUNT = 5


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
        "Je suis votre assistant direct <b>Antibes ⟷ Nice-Ville</b> (TER & Bus Ligne A).\n"
        "Je vous préviens des prochains départs, retards et perturbations.\n\n"
        "📅 <b>Alertes automatiques :</b>\n"
        "• 07:15 (Semaine) : Antibes ➔ Nice-Ville + Bus Bertone\n"
        "• 16:15 (Semaine) : Nice-Ville ➔ Antibes + Bus Pôle d'Échanges\n\n"
        "⚡ <b>Commandes disponibles :</b>\n"
        "• /trains : Prochains trains et bus selon le moment de la journée\n"
        "• /bus : Prochains bus Envibus Ligne A en direct\n"
        "• /antibes : Départs depuis Antibes vers Nice\n"
        "• /nice : Départs depuis Nice vers Antibes\n"
        "• /help : Afficher l'aide\n\n"
        "<i>Chargement des prochains départs en cours...</i>"
    )

    msg = await update.effective_message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

    sncf_client: SncfClient = context.bot_data["sncf_client"]
    envibus_client: EnvibusClient | None = context.bot_data.get("envibus_client")

    try:
        train_task = sncf_client.get_next_trains(direction, count=config.max_departures)
        bus_task = envibus_client.get_next_departures(direction, count=DEFAULT_BUS_COUNT) if envibus_client else None

        if bus_task:
            train_res, bus_res = await asyncio.gather(train_task, bus_task, return_exceptions=True)
            status = train_res if isinstance(train_res, CommuteStatus) else None
            bus_status = bus_res if isinstance(bus_res, BusCommuteStatus) else None
        else:
            status = await train_task
            bus_status = None

        if status:
            text = format_commute_message(status, bus_status)
            keyboard = make_commute_keyboard(direction)
            await msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        else:
            await msg.edit_text(
                f"{welcome_text}\n\n⚠️ <i>Impossible d'obtenir les horaires des trains.</i>",
                parse_mode=ParseMode.HTML,
            )
    except Exception as exc:
        logger.error("Failed to fetch departures on /start: %s", exc)
        await msg.edit_text(
            f"{welcome_text}\n\n⚠️ <i>Impossible d'obtenir les horaires en direct ({exc}).</i>",
            parse_mode=ParseMode.HTML,
        )


@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "ℹ️ <b>Aide - Bot TER & Envibus Antibes ⟷ Nice</b>\n\n"
        "<b>Commandes :</b>\n"
        "• /trains : Prochains trains et correspondances bus Ligne A\n"
        "• /bus : Prochains bus Envibus Ligne A en direct\n"
        "• /antibes : Prochains TER et bus au départ d'Antibes vers Nice-Ville\n"
        "• /nice : Prochains TER et bus au départ de Nice-Ville vers Antibes\n"
        "• /help : Affiche ce message d'aide\n\n"
        "<b>Boutons interactifs :</b>\n"
        "• 🔄 <b>Actualiser</b> : Rafraîchit les horaires et retards en temps réel\n"
        "• ↔️ <b>Inverser</b> : Bascule instantanément sur l'autre sens de trajet\n"
        "• 🎫 <b>TER Sud</b> / 🚌 <b>Envibus Ligne A</b> : Liens directs avec arrêts présélectionnés"
    )
    await update.effective_message.reply_text(help_text, parse_mode=ParseMode.HTML)


@restricted
async def trains_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /trains command with smart directional inference."""
    config: Config = context.bot_data["config"]
    direction = get_default_direction(config.timezone)
    await _send_departures(update, context, direction)


@restricted
async def bus_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /bus command showing standalone Envibus Line A departures."""
    config: Config = context.bot_data["config"]
    direction = get_default_direction(config.timezone)
    await _send_bus_departures(update, context, direction)


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
    """Helper to query SNCF and Envibus concurrently and reply with combined departures."""
    config: Config = context.bot_data["config"]
    client: SncfClient = context.bot_data["sncf_client"]
    envibus_client: EnvibusClient | None = context.bot_data.get("envibus_client")

    waiting_msg = await update.effective_message.reply_text(
        f"🔍 Recherche des prochains trains & bus <b>{direction.origin_name} ➔ {direction.destination_name}</b>...",
        parse_mode=ParseMode.HTML,
    )

    try:
        train_task = client.get_next_trains(direction, count=config.max_departures)
        bus_task = envibus_client.get_next_departures(direction, count=DEFAULT_BUS_COUNT) if envibus_client else None

        if bus_task:
            train_res, bus_res = await asyncio.gather(train_task, bus_task, return_exceptions=True)
            status = train_res if isinstance(train_res, CommuteStatus) else None
            bus_status = bus_res if isinstance(bus_res, BusCommuteStatus) else None
        else:
            status = await train_task
            bus_status = None

        if not status:
            raise RuntimeError("Impossible de récupérer les départs SNCF.")

        text = format_commute_message(status, bus_status)
        keyboard = make_commute_keyboard(direction)
        await waiting_msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception as exc:
        logger.error("Error fetching departures for %s: %s", direction, exc)
        await waiting_msg.edit_text(
            f"❌ <b>Erreur :</b> Impossible de récupérer les départs ({exc}).",
            parse_mode=ParseMode.HTML,
        )


async def _send_bus_departures(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    direction: CommuteDirection,
) -> None:
    """Helper to query Envibus directly and reply with standalone bus departures."""
    envibus_client: EnvibusClient | None = context.bot_data.get("envibus_client")
    if not envibus_client:
        await update.effective_message.reply_text(
            "⚠️ <i>Service Envibus non initialisé.</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    stop_name = "Collège Bertone" if direction == CommuteDirection.ANTIBES_TO_NICE else "Pôle d'Échanges d'Antibes"
    waiting_msg = await update.effective_message.reply_text(
        f"🔍 Recherche des prochains bus Ligne A à <b>{stop_name}</b>...",
        parse_mode=ParseMode.HTML,
    )

    try:
        bus_status = await envibus_client.get_next_departures(direction, count=DEFAULT_BUS_COUNT)
        if not bus_status:
            # Generate fallback empty status with correct metadata
            now = datetime.now(envibus_client.tz)
            dest_label = "Pôle d'Échanges d'Antibes" if direction == CommuteDirection.ANTIBES_TO_NICE else "Collège Bertone"
            bus_status = BusCommuteStatus(
                line_name="Ligne A",
                stop_name=stop_name,
                direction_name=dest_label,
                departures=[],
                query_time=now,
                is_live=False,
                itinerary_url=get_itinerary_url(direction),
            )

        text = format_bus_message(bus_status)
        keyboard = make_bus_keyboard(direction)
        await waiting_msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception as exc:
        logger.error("Error fetching bus departures for %s: %s", direction, exc)
        await waiting_msg.edit_text(
            f"❌ <b>Erreur :</b> Impossible de récupérer les départs du bus ({exc}).",
            parse_mode=ParseMode.HTML,
        )


@restricted
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button clicks for trains and standalone bus."""
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    config: Config = context.bot_data["config"]
    sncf_client: SncfClient = context.bot_data["sncf_client"]
    envibus_client: EnvibusClient | None = context.bot_data.get("envibus_client")

    if ":" not in data:
        await query.answer()
        return

    action, dir_str = data.split(":", 1)
    try:
        direction = CommuteDirection(dir_str)
    except ValueError:
        await query.answer("Sens inconnu.")
        return

    # Acknowledge the callback immediately
    await query.answer("Actualisation...")

    try:
        # Handle standalone bus refresh / switch
        if action in ("bus_refresh", "bus_switch"):
            if not envibus_client:
                await query.answer("Service Envibus indisponible.", show_alert=True)
                return

            bus_status = await envibus_client.get_next_departures(direction, count=DEFAULT_BUS_COUNT)
            if not bus_status:
                now = datetime.now(envibus_client.tz)
                stop_name = "Collège Bertone" if direction == CommuteDirection.ANTIBES_TO_NICE else "Pôle d'Échanges d'Antibes"
                dest_label = "Pôle d'Échanges d'Antibes" if direction == CommuteDirection.ANTIBES_TO_NICE else "Collège Bertone"
                bus_status = BusCommuteStatus(
                    line_name="Ligne A",
                    stop_name=stop_name,
                    direction_name=dest_label,
                    departures=[],
                    query_time=now,
                    is_live=False,
                    itinerary_url=get_itinerary_url(direction),
                )

            text = format_bus_message(bus_status)
            keyboard = make_bus_keyboard(direction)

            if query.message and query.message.text_html != text:
                await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            return

        # Handle combined commute refresh / switch
        train_task = sncf_client.get_next_trains(direction, count=config.max_departures)
        bus_task = envibus_client.get_next_departures(direction, count=DEFAULT_BUS_COUNT) if envibus_client else None

        if bus_task:
            train_res, bus_res = await asyncio.gather(train_task, bus_task, return_exceptions=True)
            status = train_res if isinstance(train_res, CommuteStatus) else None
            bus_status = bus_res if isinstance(bus_res, BusCommuteStatus) else None
        else:
            status = await train_task
            bus_status = None

        if not status:
            await query.answer("Erreur lors de la récupération des trains.", show_alert=True)
            return

        text = format_commute_message(status, bus_status)
        keyboard = make_commute_keyboard(direction)

        if query.message and query.message.text_html != text:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception as exc:
        logger.error("Error updating callback query %s: %s", data, exc)
        await query.answer(f"Erreur d'actualisation : {exc}", show_alert=True)
