"""Automated commute notification scheduler."""
from __future__ import annotations

import datetime
import logging
from zoneinfo import ZoneInfo
from telegram.constants import ParseMode
from telegram.ext import Application, ContextTypes

from trainbot.bot.formatter import format_commute_message, make_commute_keyboard
from trainbot.config import Config
from trainbot.sncf.client import SncfClient
from trainbot.sncf.models import CommuteDirection

logger = logging.getLogger(__name__)

# Days in python-telegram-bot JobQueue (0=Sunday, 1=Monday ... 5=Friday, 6=Saturday)
WEEKDAYS = (1, 2, 3, 4, 5)


async def broadcast_commute_status(
    context: ContextTypes.DEFAULT_TYPE,
    direction: CommuteDirection,
    title_prefix: str = "🔔 <b>Notification automatique</b>\n",
) -> None:
    """Fetch status for direction and broadcast to all whitelisted users."""
    config: Config = context.bot_data["config"]
    client: SncfClient = context.bot_data["sncf_client"]

    if not config.allowed_user_ids:
        logger.warning("No allowed users configured for broadcast.")
        return

    logger.info("Starting broadcast for direction: %s", direction.value)
    try:
        status = await client.get_next_trains(direction, count=config.max_departures)
        body = format_commute_message(status)
        text = f"{title_prefix}\n{body}"
        keyboard = make_commute_keyboard(direction)
    except Exception as exc:
        logger.error("Failed to fetch SNCF departures during broadcast: %s", exc)
        text = (
            f"{title_prefix}\n"
            f"🚄 <b>TER : {direction.origin_name} ➔ {direction.destination_name}</b>\n\n"
            f"⚠️ <i>Impossible d'obtenir les horaires en direct ({exc}).</i>"
        )
        keyboard = make_commute_keyboard(direction)

    sent_count = 0
    for user_id in config.allowed_user_ids:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
            sent_count += 1
        except Exception as exc:
            logger.warning("Failed to send scheduled broadcast to user %s: %s", user_id, exc)

    logger.info("Broadcast complete. Sent to %d / %d users.", sent_count, len(config.allowed_user_ids))


async def morning_broadcast_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """07:00 weekday job: Antibes -> Nice-Ville."""
    await broadcast_commute_status(
        context,
        direction=CommuteDirection.ANTIBES_TO_NICE,
        title_prefix="🌅 <b>Bonjour ! Voici vos trains pour Nice</b>\n",
    )


async def evening_broadcast_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """16:00 weekday job: Nice-Ville -> Antibes."""
    await broadcast_commute_status(
        context,
        direction=CommuteDirection.NICE_TO_ANTIBES,
        title_prefix="🌆 <b>Bonne fin de journée ! Voici vos trains pour Antibes</b>\n",
    )


def parse_time_string(time_str: str, tz: ZoneInfo) -> datetime.time:
    """Parse 'HH:MM' into datetime.time with timezone."""
    parts = time_str.strip().split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    return datetime.time(hour=hour, minute=minute, tzinfo=tz)


def setup_scheduler(app: Application, config: Config) -> None:
    """Register daily weekday commute broadcast jobs with JobQueue."""
    if not app.job_queue:
        logger.error("JobQueue is not initialized on Application.")
        return

    tz = ZoneInfo(config.timezone)
    morning_time = parse_time_string(config.morning_time, tz)
    evening_time = parse_time_string(config.evening_time, tz)

    # Schedule morning commute (Monday to Friday)
    app.job_queue.run_daily(
        morning_broadcast_job,
        time=morning_time,
        days=WEEKDAYS,
        name="morning_commute_antibes_to_nice",
    )

    # Schedule evening commute (Monday to Friday)
    app.job_queue.run_daily(
        evening_broadcast_job,
        time=evening_time,
        days=WEEKDAYS,
        name="evening_commute_nice_to_antibes",
    )

    logger.info(
        "Scheduled weekday broadcasts at %s (Antibes->Nice) and %s (Nice->Antibes) [%s]",
        config.morning_time,
        config.evening_time,
        config.timezone,
    )
