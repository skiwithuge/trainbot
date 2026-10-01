"""HTML message formatter and keyboard generator for Telegram."""
from __future__ import annotations

import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from trainbot.envibus.models import BusCommuteStatus, BusDeparture
from trainbot.sncf.models import CommuteDirection, CommuteStatus, TrainDeparture

ENVIBUS_SCHEDULE_URL = "https://www.envibus.fr"


def format_departure_card(dep: TrainDeparture) -> str:
    """Format an individual train departure entry."""
    sched_time = dep.scheduled_departure.strftime("%H:%M")
    real_time = dep.realtime_departure.strftime("%H:%M")

    # Time and delay badge
    if dep.is_cancelled:
        time_line = f"⏰ <s>{sched_time}</s> <b>{dep.status_summary}</b>"
    elif dep.delay_minutes > 0:
        time_line = f"⏰ <s>{sched_time}</s> <b>{real_time}</b> ({dep.status_summary})"
    else:
        time_line = f"⏰ <b>{sched_time}</b> ({dep.status_summary})"

    # Train details
    platform_info = f" • Voie <b>{html.escape(dep.platform)}</b>" if dep.platform else ""
    mode_label = html.escape(dep.commercial_mode) if dep.commercial_mode else "TER"
    details_line = f"🚆 {mode_label} {html.escape(dep.train_number)} ➔ {html.escape(dep.destination)}{platform_info}"

    lines = [time_line, details_line]

    if dep.disruptions:
        for dis in dep.disruptions:
            lines.append(f"⚠️ {dis}")

    return "\n".join(lines)


def format_bus_section(status: BusCommuteStatus) -> str:
    """Format the Envibus Line A departure block for combined commute messages."""
    lines = [f"🚌 <b>Envibus Ligne A ({status.stop_name} ➔ {status.direction_name}) :</b>"]
    for dep in status.departures:
        mins_text = f"Dans {dep.minutes_away} min" if dep.minutes_away > 0 else "À l'approche"
        lines.append(f"• ⚡ <b>{mins_text}</b> ({dep.formatted_time})")
    return "\n".join(lines)


def format_bus_message(status: BusCommuteStatus) -> str:
    """Format standalone bus message for /bus command."""
    q_time = status.query_time.strftime("%H:%M")
    header = (
        f"🚌 <b>Envibus Ligne A : {status.stop_name} ➔ {status.direction_name}</b>\n"
        f"<i>Mis à jour à {q_time}</i>\n"
    )

    if not status.has_departures:
        body = "\nℹ️ <i>Aucun bus en circulation en temps réel actuellement.</i>\n"
    else:
        dep_lines = []
        for dep in status.departures:
            mins_text = f"Dans {dep.minutes_away} min" if dep.minutes_away > 0 else "À l'approche"
            dep_lines.append(f"• ⚡ <b>{mins_text}</b> ({dep.formatted_time}) ➔ {html.escape(dep.destination)}")
        body = "\n" + "\n".join(dep_lines) + "\n"

    return f"{header}{body}"


def format_commute_message(
    status: CommuteStatus,
    bus_status: BusCommuteStatus | None = None,
) -> str:
    """Format full commute status (trains + optional bus section) into an HTML message."""
    orig = status.direction.origin_name
    dest = status.direction.destination_name
    q_time = status.query_time.strftime("%H:%M")

    header = f"🚄 <b>{orig} ➔ {dest}</b>\n<i>Mis à jour à {q_time}</i>\n"

    if not status.departures:
        body = "\n<i>Aucun train régional prévu dans les prochaines heures.</i>\n"
    else:
        cards = [format_departure_card(dep) for dep in status.departures]
        body = "\n\n".join(cards)

    bus_section = ""
    if bus_status and bus_status.has_departures:
        bus_section = f"\n\n{format_bus_section(bus_status)}"

    disruption_section = ""
    if status.general_disruptions:
        dis_items = "\n".join(f"• {d}" for d in status.general_disruptions[:3])
        disruption_section = f"\n\n📢 <b>Infos Trafic SNCF :</b>\n{dis_items}"

    return f"{header}\n{body}{bus_section}{disruption_section}"


def make_commute_keyboard(direction: CommuteDirection) -> InlineKeyboardMarkup:
    """Generate refresh, direction-switch, and external service link buttons."""
    reverse_dir = direction.reverse
    reverse_label = f"↔️ Vers {reverse_dir.destination_name}"

    keyboard = [
        [
            InlineKeyboardButton("🔄 Actualiser", callback_data=f"refresh:{direction.value}"),
            InlineKeyboardButton(reverse_label, callback_data=f"switch:{reverse_dir.value}"),
        ],
        [
            InlineKeyboardButton("🎫 TER Sud", url=direction.ter_url),
            InlineKeyboardButton("🚌 Envibus Ligne A", url=ENVIBUS_SCHEDULE_URL),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def make_bus_keyboard(direction: CommuteDirection) -> InlineKeyboardMarkup:
    """Generate inline keyboard for standalone /bus message."""
    reverse_dir = direction.reverse
    reverse_label = f"↔️ Sens inverse"

    keyboard = [
        [
            InlineKeyboardButton("🔄 Actualiser", callback_data=f"bus_refresh:{direction.value}"),
            InlineKeyboardButton(reverse_label, callback_data=f"bus_switch:{reverse_dir.value}"),
        ],
        [
            InlineKeyboardButton("🚌 Fiche Horaires Ligne A", url=ENVIBUS_SCHEDULE_URL),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
