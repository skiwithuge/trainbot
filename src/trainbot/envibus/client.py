"""Async client for Envibus real-time departures (web scraping Instant System)."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
import httpx

from trainbot.envibus.models import BusCommuteStatus, BusDeparture
from trainbot.sncf.models import CommuteDirection

logger = logging.getLogger(__name__)

LINE_A_ID = "ENVIBUS:0-70"
LINE_A_NAME = "Ligne A"

# Morning (Bertone -> Pole d'Echanges d'Antibes)
BERTONE_SLUG = "college-bertone"
BERTONE_STOP_ID = "ENVIBUS:0-158"
BERTONE_STOP_NAME = "Collège Bertone"
BERTONE_TARGET_NAME = "Pôle d'Échanges d'Antibes"
BERTONE_DIRECTION = "RETURN"
BERTONE_STOPAREA_ID = "STOPAREA|ENVIBUSSCHOLAR:158"
BERTONE_STOPAREA_LABEL = "COLLEGE BERTONE, Antibes"
BERTONE_LAT = "43.59329"
BERTONE_LON = "7.09967"

# Evening (Pole d'Echanges d'Antibes -> Collège Bertone)
POLE_SLUG = "pole-dechanges"
POLE_STOP_ID = "ENVIBUS:0-1126"
POLE_STOP_NAME = "Pôle d'Échanges d'Antibes"
POLE_TARGET_NAME = "Collège Bertone"
POLE_DIRECTION = "OUTWARD"
POLE_STOPAREA_ID = "STOPAREA|ISSTOPPLACE:ENVIBUS:0-2837:ENVIBUS:0-2836"
POLE_STOPAREA_LABEL = "POLE D'ECHANGES ANTIBES, Antibes"
POLE_LAT = "43.5863"
POLE_LON = "7.11896"

WEB_BASE_URL = "https://47.prod-sim.instant-system.com"
ITINERAIRES_BASE_URL = "https://www.envibus.fr/le-reseau/itineraires"


def get_itinerary_url(commute_dir: CommuteDirection) -> str:
    """Return the official Envibus journey URL with preselected origin and destination."""
    if commute_dir == CommuteDirection.ANTIBES_TO_NICE:
        from_id, from_val, from_lat, from_lon = (
            BERTONE_STOPAREA_ID,
            BERTONE_STOPAREA_LABEL,
            BERTONE_LAT,
            BERTONE_LON,
        )
        to_id, to_val, to_lat, to_lon = (
            POLE_STOPAREA_ID,
            POLE_STOPAREA_LABEL,
            POLE_LAT,
            POLE_LON,
        )
    else:
        from_id, from_val, from_lat, from_lon = (
            POLE_STOPAREA_ID,
            POLE_STOPAREA_LABEL,
            POLE_LAT,
            POLE_LON,
        )
        to_id, to_val, to_lat, to_lon = (
            BERTONE_STOPAREA_ID,
            BERTONE_STOPAREA_LABEL,
            BERTONE_LAT,
            BERTONE_LON,
        )

    params = {
        "product": "place-journey-map",
        "redirection": "true",
        "internal": "true",
        "isfid": from_id,
        "isfv": from_val,
        "isflat": from_lat,
        "isflon": from_lon,
        "istid": to_id,
        "istv": to_val,
        "istlat": to_lat,
        "istlon": to_lon,
        "m": "train-bus-bike-car-walk-park-bikepark-parkandride-ridesharing",
        "ws": "1",
        "bs": "1",
        "df": "true",
        "a": "false",
        "sl": "INCLUDE",
        "ad": "false",
        "c": "FASTEST",
    }
    return f"{ITINERAIRES_BASE_URL}?{urlencode(params)}#is-Journey-Mode_TRANSPORT"


class EnvibusClient:
    """Client for scraping upcoming Envibus Line A live departures from web."""

    def __init__(
        self,
        timezone: str = "Europe/Paris",
        mock_mode: bool = False,
        base_url: str = WEB_BASE_URL,
        timeout: float = 5.0,
    ) -> None:
        self.timezone_str = timezone
        self.tz = ZoneInfo(timezone)
        self.mock_mode = mock_mode
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get_next_departures(
        self,
        commute_dir: CommuteDirection,
        count: int = 5,
    ) -> BusCommuteStatus | None:
        """Fetch next bus departures (real-time supplemented by scheduled) for the commute direction.

        Returns None if request fails or no departures are available.
        """
        if self.mock_mode:
            return self._generate_mock_status(commute_dir, count)

        direction_code, slug, stop_id, stop_name, target_name = self._resolve_commute_params(commute_dir)

        url = f"{self.base_url}/fr/horaires/ligne/{LINE_A_ID}/direction/{direction_code}/arret/{slug}/{stop_id}"
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html, */*; q=0.01",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    logger.warning("Envibus web returned HTTP %d for stop %s", resp.status_code, stop_id)
                    return None

                html_text = resp.text
                departures = self._parse_departures(html_text, count)
                now = datetime.now(self.tz)

                return BusCommuteStatus(
                    line_name=LINE_A_NAME,
                    stop_name=stop_name,
                    direction_name=target_name,
                    departures=departures,
                    query_time=now,
                    is_live=any(d.is_realtime for d in departures),
                    itinerary_url=get_itinerary_url(commute_dir),
                )
        except Exception as exc:
            logger.warning("Failed to fetch Envibus departures for stop %s: %s", stop_id, exc)
            return None

    def _resolve_commute_params(
        self,
        commute_dir: CommuteDirection,
    ) -> tuple[str, str, str, str, str]:
        """Resolve direction, URL slug, stop ID, stop name, and target direction name."""
        if commute_dir == CommuteDirection.ANTIBES_TO_NICE:
            # Morning: Bertone towards Pole d'Echanges / Gare d'Antibes
            return (BERTONE_DIRECTION, BERTONE_SLUG, BERTONE_STOP_ID, BERTONE_STOP_NAME, BERTONE_TARGET_NAME)
        # Evening: Pole d'Echanges towards Bertone / Valbonne
        return (POLE_DIRECTION, POLE_SLUG, POLE_STOP_ID, POLE_STOP_NAME, POLE_TARGET_NAME)

    def _parse_departures(self, html_text: str, count: int) -> list[BusDeparture]:
        """Parse live real-time departures only."""
        dest_match = re.search(r"is-Schedule-Line-Directions-Item-Label[^>]*>\s*(?:Destination\s*)?([^<]+)<", html_text)
        destination = dest_match.group(1).strip() if dest_match else "Antibes"

        # Parse live real-time departures
        pattern = r"<span[^>]*class=\"[^\"]*is-Schedule-Line-Directions-Item-Time-C2[^\"]*is-realtime[^\"]*\"[^>]*>\s*(\d+)"
        matches = re.findall(pattern, html_text)

        departures: list[BusDeparture] = []
        now = datetime.now(self.tz)

        for minute_str in matches[:count]:
            try:
                mins = int(minute_str)
                est_time = now + timedelta(minutes=mins)
                departures.append(
                    BusDeparture(
                        minutes_away=mins,
                        estimated_time=est_time,
                        destination=destination,
                        is_realtime=True,
                    )
                )
            except ValueError:
                continue

        return departures

    def _generate_mock_status(self, commute_dir: CommuteDirection, count: int) -> BusCommuteStatus:
        """Generate realistic mock bus departures (more than 3) for local testing."""
        _, _, _, stop_name, target_name = self._resolve_commute_params(commute_dir)
        now = datetime.now(self.tz)

        mock_minutes = [4, 14, 24, 36, 48][:count]
        dest = "Antibes les Pins" if commute_dir == CommuteDirection.ANTIBES_TO_NICE else "G.R. Valbonne"

        departures = [
            BusDeparture(
                minutes_away=m,
                estimated_time=now + timedelta(minutes=m),
                destination=dest,
                is_realtime=True,
            )
            for m in mock_minutes
        ]

        return BusCommuteStatus(
            line_name=LINE_A_NAME,
            stop_name=stop_name,
            direction_name=target_name,
            departures=departures,
            query_time=now,
            is_live=True,
            itinerary_url=get_itinerary_url(commute_dir),
        )
