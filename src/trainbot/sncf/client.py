"""Async client for the SNCF / Navitia API."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo
import httpx

from trainbot.sncf.models import CommuteDirection, CommuteStatus, TrainDeparture

logger = logging.getLogger(__name__)

SNCF_API_BASE = "https://api.sncf.com/v1/coverage/sncf"


class SncfClient:
    """Client for retrieving real-time TER train departures and disruptions."""

    def __init__(self, api_key: str, timezone: str = "Europe/Paris", mock_mode: bool = False):
        self.api_key = api_key
        self.tz = ZoneInfo(timezone)
        self.mock_mode = mock_mode

    def _parse_api_datetime(self, dt_str: str) -> datetime:
        """Parse Navitia API datetime format YYYYMMDDTHHMMSS into timezone-aware datetime."""
        # e.g. "20260928T161500"
        naive = datetime.strptime(dt_str, "%Y%m%dT%H%M%S")
        return naive.replace(tzinfo=self.tz)

    async def get_next_trains(
        self,
        direction: CommuteDirection,
        count: int = 4,
        from_time: datetime | None = None,
    ) -> CommuteStatus:
        """Fetch next direct TER trains for the given direction with real-time status."""
        if self.mock_mode or not self.api_key:
            return self._generate_mock_status(direction, from_time)

        now = from_time or datetime.now(self.tz)
        dt_param = now.strftime("%Y%m%dT%H%M%S")

        params = {
            "from": direction.origin_id,
            "to": direction.destination_id,
            "datetime": dt_param,
            "datetime_represents": "departure",
            "data_freshness": "realtime",
            "min_nb_journeys": max(count * 2, 6),
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(
                    f"{SNCF_API_BASE}/journeys",
                    params=params,
                    auth=(self.api_key, ""),
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as exc:
                logger.error("SNCF API error status %s: %s", exc.response.status_code, exc.response.text)
                raise RuntimeError(f"Erreur API SNCF ({exc.response.status_code})") from exc
            except Exception as exc:
                logger.error("Failed to connect to SNCF API: %s", exc)
                raise RuntimeError("Impossible de joindre le service SNCF pour le moment.") from exc

        return self._parse_journeys_response(data, direction, now, count)

    def _parse_journeys_response(
        self,
        data: dict[str, Any],
        direction: CommuteDirection,
        query_time: datetime,
        count: int,
    ) -> CommuteStatus:
        """Parse raw Navitia journeys response into typed CommuteStatus."""
        departures: list[TrainDeparture] = []
        general_disruptions: set[str] = set()

        # Parse global disruptions if present
        for dis in data.get("disruptions", []):
            for msg in dis.get("messages", []):
                text = msg.get("text", "").strip()
                if text:
                    general_disruptions.add(text)

        journeys = data.get("journeys", [])
        for journey in journeys:
            # Only consider direct journeys
            if journey.get("nb_transfers", 0) > 0:
                continue

            status_str = journey.get("status", "")
            is_cancelled = status_str == "NO_SERVICE"

            # Find the main public transport section
            pt_section = None
            for section in journey.get("sections", []):
                if section.get("type") == "public_transport":
                    pt_section = section
                    break

            if not pt_section:
                continue

            disp_info = pt_section.get("display_informations", {})
            commercial_mode = disp_info.get("commercial_mode", "").strip()
            network = disp_info.get("network", "").strip()
            physical_mode = disp_info.get("physical_mode", "").lower()

            # Exclude replacement buses and coaches (rail trains only)
            if any(road_mode in physical_mode for road_mode in ("bus", "coach", "car", "autocar")):
                continue

            # Exclude long-distance services
            comm_upper = commercial_mode.upper()
            excluded_modes = ("TGV", "OUIGO", "INTERCIT", "EUROSTAR", "FRECCIAROSSA")
            if any(excl in comm_upper for excl in excluded_modes):
                continue

            # Match regional services: TER, ZOU!, or Région Sud
            net_upper = network.upper()
            is_regional = (
                "TER" in comm_upper
                or "ZOU" in comm_upper
                or "TER" in net_upper
                or "ZOU" in net_upper
                or "REGION" in net_upper
            )
            if not is_regional:
                continue

            display_mode = commercial_mode if commercial_mode else "TER"
            train_number = disp_info.get("headsign") or disp_info.get("code") or display_mode
            destination = disp_info.get("direction", direction.destination_name)

            # Scheduled vs Realtime departure times
            sched_str = pt_section.get("base_departure_date_time") or pt_section.get("departure_date_time")
            real_str = pt_section.get("departure_date_time") or sched_str

            if not sched_str:
                continue

            scheduled_dt = self._parse_api_datetime(sched_str)
            realtime_dt = self._parse_api_datetime(real_str)

            delay_minutes = int((realtime_dt - scheduled_dt).total_seconds() // 60)

            # Extract platform if available
            from_stop = pt_section.get("from", {}).get("stop_point", {})
            platform = from_stop.get("platform_code")

            # Extract section disruptions
            section_disruptions: list[str] = []
            for dis in pt_section.get("disruptions", []):
                for msg in dis.get("messages", []):
                    msg_text = msg.get("text", "").strip()
                    if msg_text:
                        section_disruptions.append(msg_text)
                        general_disruptions.add(msg_text)

            departures.append(
                TrainDeparture(
                    train_number=train_number,
                    commercial_mode=display_mode,
                    destination=destination,
                    scheduled_departure=scheduled_dt,
                    realtime_departure=realtime_dt,
                    delay_minutes=delay_minutes,
                    is_cancelled=is_cancelled,
                    platform=platform,
                    disruptions=section_disruptions,
                )
            )

            if len(departures) >= count:
                break

        return CommuteStatus(
            direction=direction,
            query_time=query_time,
            departures=departures,
            general_disruptions=sorted(general_disruptions),
        )

    def _generate_mock_status(
        self,
        direction: CommuteDirection,
        from_time: datetime | None = None,
    ) -> CommuteStatus:
        """Provide realistic mock train departures for testing and development."""
        from datetime import timedelta

        base_time = from_time or datetime.now(self.tz)
        mock_departures = [
            TrainDeparture(
                train_number="86012",
                commercial_mode="TER",
                destination="Vintimille" if direction == CommuteDirection.ANTIBES_TO_NICE else "Grasse",
                scheduled_departure=base_time + timedelta(minutes=10),
                realtime_departure=base_time + timedelta(minutes=10),
                delay_minutes=0,
                is_cancelled=False,
                platform="A",
            ),
            TrainDeparture(
                train_number="86016",
                commercial_mode="TER",
                destination="Nice-Ville" if direction == CommuteDirection.ANTIBES_TO_NICE else "Cannes-la-Bocca",
                scheduled_departure=base_time + timedelta(minutes=25),
                realtime_departure=base_time + timedelta(minutes=37),
                delay_minutes=12,
                is_cancelled=False,
                platform="B",
                disruptions=["Retard de 12 min suite à une régulation du trafic."],
            ),
            TrainDeparture(
                train_number="86020",
                commercial_mode="TER",
                destination="Monaco Monte-Carlo" if direction == CommuteDirection.ANTIBES_TO_NICE else "Les Arcs Draguignan",
                scheduled_departure=base_time + timedelta(minutes=45),
                realtime_departure=base_time + timedelta(minutes=45),
                delay_minutes=0,
                is_cancelled=False,
                platform="A",
            ),
            TrainDeparture(
                train_number="86024",
                commercial_mode="TER",
                destination="Vintimille" if direction == CommuteDirection.ANTIBES_TO_NICE else "Grasse",
                scheduled_departure=base_time + timedelta(minutes=60),
                realtime_departure=base_time + timedelta(minutes=60),
                delay_minutes=0,
                is_cancelled=True,
                platform=None,
                disruptions=["Train supprimé en raison d'une panne de matériel."],
            ),
        ]

        return CommuteStatus(
            direction=direction,
            query_time=base_time,
            departures=mock_departures,
            general_disruptions=["Travaux de maintenance nocturne prévus sur l'axe Cannes-Nice."],
        )
