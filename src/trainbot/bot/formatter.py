"""HTML message formatter and keyboard generator for Telegram."""
from __future__ import annotations

import html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from trainbot.sncf.models import CommuteDirection, CommuteStatus, TrainDeparture


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
    details_line = f"🚆 TER {html.escape(dep.train_number)} ➔ {html.escape(dep.destination)}{platform_info}"

    lines = [time_line, details_line]

    if dep.disruptions:
        for dis in dep.disruptions:
            lines.append(f"⚠️ <i>{html.escape(dis)}</i>")

    return "\n".join(lines)


def format_commute_message(status: CommuteStatus) -> str:
    """Format full commute status into an attractive Telegram HTML message."""
    orig = status.direction.origin_name
    dest = status.direction.destination_name
    q_time = status.query_time.strftime("%H:%M")

    header = f"🚄 <b>TER : {orig} ➔ {dest}</b>\n<i>Mis à jour à {q_time}</i>\n"

    if not status.departures:
        body = "\n<i>Aucun train TER prévu dans les prochaines heures.</i>\n"
    else:
        cards = [format_departure_card(dep) for dep in status.departures]
        body = "\n\n".join(cards)

    disruption_section = ""
    if status.general_disruptions:
        dis_items = "\n".join(f"• <i>{html.escape(d)}</i>" for d in status.general_disruptions[:3])
        disruption_section = f"\n\n📢 <b>Infos Trafic :</b>\n{dis_items}"

    return f"{header}\n{body}{disruption_section}"


def make_commute_keyboard(direction: CommuteDirection) -> InlineKeyboardMarkup:
    """Generate refresh and direction-switch buttons."""
    reverse_dir = direction.reverse
    reverse_label = f"↔️ Vers {reverse_dir.destination_name}"

    keyboard = [
        [
            InlineKeyboardButton("🔄 Actualiser", callback_data=f"refresh:{direction.value}"),
            InlineKeyboardButton(reverse_label, callback_data=f"switch:{reverse_dir.value}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
