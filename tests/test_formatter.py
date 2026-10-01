from datetime import datetime
from zoneinfo import ZoneInfo
from trainbot.bot.formatter import (
    format_bus_message,
    format_bus_section,
    format_commute_message,
    make_bus_keyboard,
    make_commute_keyboard,
)
from trainbot.envibus.models import BusCommuteStatus, BusDeparture
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


def test_format_commute_message_with_bus_section():
    tz = ZoneInfo("Europe/Paris")
    q_time = datetime(2026, 9, 28, 7, 0, tzinfo=tz)

    train_status = CommuteStatus(
        direction=CommuteDirection.ANTIBES_TO_NICE,
        query_time=q_time,
        departures=[],
    )

    bus_dep = BusDeparture(
        minutes_away=8,
        estimated_time=datetime(2026, 9, 28, 7, 8, tzinfo=tz),
        destination="Antibes les Pins",
        is_realtime=True,
    )
    bus_status = BusCommuteStatus(
        line_name="Ligne A",
        stop_name="Collège Bertone",
        direction_name="Pôle d'Échanges d'Antibes",
        departures=[bus_dep],
        query_time=q_time,
        itinerary_url="https://www.envibus.fr/le-reseau/itineraires?product=place-journey-map",
    )

    msg = format_commute_message(train_status, bus_status)
    assert "Envibus Ligne A (Collège Bertone ➔ Pôle d'Échanges d'Antibes)" in msg
    assert "Dans 8 min" in msg
    assert "07:08" in msg
    assert "https://www.envibus.fr/le-reseau/itineraires" in msg


def test_format_bus_message_standalone():
    tz = ZoneInfo("Europe/Paris")
    q_time = datetime(2026, 9, 28, 16, 0, tzinfo=tz)

    bus_dep = BusDeparture(
        minutes_away=5,
        estimated_time=datetime(2026, 9, 28, 16, 5, tzinfo=tz),
        destination="G.R. Valbonne",
        is_realtime=True,
    )
    bus_status = BusCommuteStatus(
        line_name="Ligne A",
        stop_name="Pôle d'Échanges d'Antibes",
        direction_name="Collège Bertone",
        departures=[bus_dep],
        query_time=q_time,
        itinerary_url="https://www.envibus.fr/le-reseau/itineraires?product=place-journey-map",
    )

    msg = format_bus_message(bus_status)
    assert "Pôle d'Échanges d'Antibes ➔ Collège Bertone" in msg
    assert "Dans 5 min" in msg
    assert "16:05" in msg
    assert "G.R. Valbonne" in msg

    # Empty status
    empty_status = BusCommuteStatus(
        line_name="Ligne A",
        stop_name="Collège Bertone",
        direction_name="Pôle d'Échanges d'Antibes",
        departures=[],
        query_time=q_time,
    )
    empty_msg = format_bus_message(empty_status)
    assert "Aucun bus prévu ou en circulation actuellement." in empty_msg


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
    assert len(row1) == 2
    assert row1[0].text == "🎫 TER Sud"
    assert row1[0].url == "https://www.ter.sncf.com/sud-provence-alpes-cote-d-azur/se-deplacer/prochains-departs/antibes-87757674"
    assert row1[1].text == "🚌 Envibus Ligne A"
    assert "itineraires?product=place-journey-map" in row1[1].url
    assert "ENVIBUSSCHOLAR" in row1[1].url


def test_make_bus_keyboard():
    kb = make_bus_keyboard(CommuteDirection.ANTIBES_TO_NICE)
    assert len(kb.inline_keyboard) == 2

    row0 = kb.inline_keyboard[0]
    assert len(row0) == 2
    assert row0[0].text == "🔄 Actualiser"
    assert row0[0].callback_data == "bus_refresh:antibes_to_nice"
    assert "Sens inverse" in row0[1].text
    assert row0[1].callback_data == "bus_switch:nice_to_antibes"

    row1 = kb.inline_keyboard[1]
    assert len(row1) == 1
    assert row1[0].text == "🚌 Itinéraire Ligne A"
    assert "itineraires?product=place-journey-map" in row1[0].url
    assert "ENVIBUSSCHOLAR" in row1[0].url
