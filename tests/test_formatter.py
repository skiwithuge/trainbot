from datetime import datetime
from zoneinfo import ZoneInfo
from trainbot.bot.formatter import format_commute_message, make_commute_keyboard
from trainbot.sncf.models import CommuteDirection, CommuteStatus, TrainDeparture


def test_format_commute_message_on_time():
    tz = ZoneInfo("Europe/Paris")
    q_time = datetime(2026, 9, 28, 7, 0, tzinfo=tz)
    dep_time = datetime(2026, 9, 28, 7, 15, tzinfo=tz)

    dep = TrainDeparture(
        train_number="86010",
        commercial_mode="TER",
        destination="Nice-Ville",
        scheduled_departure=dep_time,
        realtime_departure=dep_time,
        delay_minutes=0,
        is_cancelled=False,
        platform="A",
    )

    status = CommuteStatus(
        direction=CommuteDirection.ANTIBES_TO_NICE,
        query_time=q_time,
        departures=[dep],
        general_disruptions=[],
    )

    msg = format_commute_message(status)
    assert "Antibes ➔ Nice-Ville" in msg
    assert "07:15" in msg
    assert "À l'heure" in msg
    assert "TER 86010" in msg
    assert "Voie <b>A</b>" in msg

    # Test ZOU! badge
    dep_zou = TrainDeparture(
        train_number="86012",
        commercial_mode="ZOU !",
        destination="Nice-Ville",
        scheduled_departure=dep_time,
        realtime_departure=dep_time,
        delay_minutes=0,
        is_cancelled=False,
    )
    status_zou = CommuteStatus(
        direction=CommuteDirection.ANTIBES_TO_NICE,
        query_time=q_time,
        departures=[dep_zou],
    )
    msg_zou = format_commute_message(status_zou)
    assert "ZOU ! 86012" in msg_zou


def test_format_commute_message_delayed_and_cancelled():
    tz = ZoneInfo("Europe/Paris")
    q_time = datetime(2026, 9, 28, 16, 0, tzinfo=tz)

    dep_delayed = TrainDeparture(
        train_number="86012",
        commercial_mode="TER",
        destination="Antibes",
        scheduled_departure=datetime(2026, 9, 28, 16, 10, tzinfo=tz),
        realtime_departure=datetime(2026, 9, 28, 16, 25, tzinfo=tz),
        delay_minutes=15,
        is_cancelled=False,
        platform="2",
        disruptions=["Panne de signalisation"],
    )

    dep_cancelled = TrainDeparture(
        train_number="86014",
        commercial_mode="TER",
        destination="Antibes",
        scheduled_departure=datetime(2026, 9, 28, 16, 30, tzinfo=tz),
        realtime_departure=datetime(2026, 9, 28, 16, 30, tzinfo=tz),
        delay_minutes=0,
        is_cancelled=True,
    )

    status = CommuteStatus(
        direction=CommuteDirection.NICE_TO_ANTIBES,
        query_time=q_time,
        departures=[dep_delayed, dep_cancelled],
        general_disruptions=["Grève locale interprofessionnelle."],
    )

    msg = format_commute_message(status)
    assert "Nice-Ville ➔ Antibes" in msg
    assert "16:25" in msg
    assert "Retard +15 min" in msg
    assert "Supprimé" in msg
    assert "Panne de signalisation" in msg
    assert "Grève locale interprofessionnelle." in msg


def test_make_commute_keyboard():
    kb = make_commute_keyboard(CommuteDirection.ANTIBES_TO_NICE)
    assert len(kb.inline_keyboard) == 2
    
    row0 = kb.inline_keyboard[0]
    assert len(row0) == 2
    assert row0[0].text == "🔄 Actualiser"
    assert row0[0].callback_data == "refresh:antibes_to_nice"
    assert "Vers Antibes" in row0[1].text
    assert row0[1].callback_data == "switch:nice_to_antibes"

    row1 = kb.inline_keyboard[1]
    assert len(row1) == 1
    assert row1[0].text == "🎫 SNCF Connect"
    assert "origin=Antibes" in row1[0].url
    assert "destination=Nice-Ville" in row1[0].url

    kb_reverse = make_commute_keyboard(CommuteDirection.NICE_TO_ANTIBES)
    row1_rev = kb_reverse.inline_keyboard[1]
    assert "origin=Nice-Ville" in row1_rev[0].url
    assert "destination=Antibes" in row1_rev[0].url

