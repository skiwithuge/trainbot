"""Tests for Envibus Line A client, models, and parser."""
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from trainbot.envibus.client import EnvibusClient
from trainbot.envibus.models import BusCommuteStatus, BusDeparture
from trainbot.sncf.models import CommuteDirection


def test_bus_departure_properties():
    tz = ZoneInfo("Europe/Paris")
    est_time = datetime(2026, 10, 1, 8, 15, tzinfo=tz)

    dep1 = BusDeparture(
        minutes_away=9,
        estimated_time=est_time,
        destination="Antibes les Pins",
        is_realtime=True,
    )
    assert dep1.formatted_time == "08:15"
    assert dep1.status_summary == "Dans 9 min (08:15)"

    dep_now = BusDeparture(
        minutes_away=0,
        estimated_time=est_time,
        destination="Antibes les Pins",
        is_realtime=True,
    )
    assert dep_now.status_summary == "À l'approche (08:15)"


def test_bus_commute_status():
    status_empty = BusCommuteStatus(
        line_name="Ligne A",
        stop_name="Collège Bertone",
        direction_name="Pôle d'Échanges d'Antibes",
        departures=[],
    )
    assert not status_empty.has_departures

    dep = BusDeparture(
        minutes_away=5,
        estimated_time=datetime.now(),
        destination="Antibes",
    )
    status_with_dep = BusCommuteStatus(
        line_name="Ligne A",
        stop_name="Collège Bertone",
        direction_name="Pôle d'Échanges d'Antibes",
        departures=[dep],
    )
    assert status_with_dep.has_departures


@pytest.mark.asyncio
async def test_envibus_client_mock_mode():
    client = EnvibusClient(mock_mode=True)

    morning = await client.get_next_departures(CommuteDirection.ANTIBES_TO_NICE, count=2)
    assert morning is not None
    assert morning.stop_name == "Collège Bertone"
    assert morning.direction_name == "Pôle d'Échanges d'Antibes"
    assert len(morning.departures) == 2
    assert morning.departures[0].minutes_away == 4
    assert morning.departures[1].minutes_away == 16

    evening = await client.get_next_departures(CommuteDirection.NICE_TO_ANTIBES, count=3)
    assert evening is not None
    assert evening.stop_name == "Pôle d'Échanges d'Antibes"
    assert evening.direction_name == "Collège Bertone"
    assert len(evening.departures) == 3


def test_envibus_parser_realtime_html():
    client = EnvibusClient()
    sample_html = """
    <p class="is-Schedule-Line-Directions-Content">
        <span class="is-Schedule-Line-Directions-Item-Label">
            Destination ANTIBES LES PINS
        </span>
        <span class="is-Schedule-Line-Directions-Item-Time">
            <span class="is-Schedule-Line-Directions-Item-Time-C1">
                <span class="is-Schedule-Line-Directions-Item-Time-C2 is-realtime" >
                    7<abbr title="minutes" aria-label="minutes" lang="fr" class="is-Unit">min</abbr>
                </span>
                <span class="is-Schedule-Line-Directions-Item-Time-C2 is-realtime" >
                    18<abbr title="minutes" aria-label="minutes" lang="fr" class="is-Unit">min</abbr>
                </span>
                <span class="is-Schedule-Line-Directions-Item-Time-C2 is-realtime" >
                    29<abbr title="minutes" aria-label="minutes" lang="fr" class="is-Unit">min</abbr>
                </span>
            </span>
        </span>
    </p>
    """

    departures = client._parse_realtime_departures(sample_html, count=2)
    assert len(departures) == 2
    assert departures[0].minutes_away == 7
    assert departures[0].destination == "ANTIBES LES PINS"
    assert departures[1].minutes_away == 18


def test_envibus_parser_empty_html():
    client = EnvibusClient()
    empty_html = "<div class='is-Alert'>Il n'y a pas de prochain départ</div>"
    departures = client._parse_realtime_departures(empty_html, count=3)
    assert len(departures) == 0
