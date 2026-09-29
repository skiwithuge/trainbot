"""Data models for train departures, delays, and disruptions."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class CommuteDirection(str, Enum):
    ANTIBES_TO_NICE = "antibes_to_nice"
    NICE_TO_ANTIBES = "nice_to_antibes"

    @property
    def origin_name(self) -> str:
        return "Antibes" if self == CommuteDirection.ANTIBES_TO_NICE else "Nice-Ville"

    @property
    def destination_name(self) -> str:
        return "Nice-Ville" if self == CommuteDirection.ANTIBES_TO_NICE else "Antibes"

    @property
    def origin_id(self) -> str:
        return "stop_area:SNCF:87757674" if self == CommuteDirection.ANTIBES_TO_NICE else "stop_area:SNCF:87756056"

    @property
    def destination_id(self) -> str:
        return "stop_area:SNCF:87756056" if self == CommuteDirection.ANTIBES_TO_NICE else "stop_area:SNCF:87757674"

    @property
    def reverse(self) -> CommuteDirection:
        return (
            CommuteDirection.NICE_TO_ANTIBES
            if self == CommuteDirection.ANTIBES_TO_NICE
            else CommuteDirection.ANTIBES_TO_NICE
        )

    def build_sncf_voyageurs_url(self, at_time: datetime | None = None) -> str:
        from datetime import datetime, timezone
        from urllib.parse import urlencode

        antibes = {
            "Label": "Antibes",
            "Type": "ZONE_ARRET",
            "Code": "OCE87757674",
            "Lng": "7.1199131",
            "Lat": "43.58597093",
        }
        nice = {
            "Label": "Nice",
            "Type": "ZONE_ARRET",
            "Code": "OCE87756056",
            "Lng": "7.261904",
            "Lat": "43.704556",
        }

        if self == CommuteDirection.ANTIBES_TO_NICE:
            dep, arr = antibes, nice
        else:
            dep, arr = nice, antibes

        dt = at_time or datetime.now(timezone.utc)
        date_str = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

        params = {
            "departureLabel": dep["Label"],
            "departureType": dep["Type"],
            "departureCode": dep["Code"],
            "departureLng": dep["Lng"],
            "departureLat": dep["Lat"],
            "arrivalLabel": arr["Label"],
            "arrivalType": arr["Type"],
            "arrivalCode": arr["Code"],
            "arrivalLng": arr["Lng"],
            "arrivalLat": arr["Lat"],
            "date": date_str,
            "sens": "PARTIR_APRES",
        }
        return f"https://www.sncf-voyageurs.com/en/travel-with-us/timetables-and-itineraries/itineraries/itineraries-details/?{urlencode(params)}"

    @property
    def sncf_voyageurs_url(self) -> str:
        return self.build_sncf_voyageurs_url()





@dataclass(frozen=True)
class TrainDeparture:
    train_number: str
    commercial_mode: str
    destination: str
    scheduled_departure: datetime
    realtime_departure: datetime
    delay_minutes: int
    is_cancelled: bool
    platform: str | None = None
    disruptions: list[str] = field(default_factory=list)

    @property
    def status_summary(self) -> str:
        if self.is_cancelled:
            return "🔴 Supprimé"
        if self.delay_minutes > 0:
            return f"🟠 Retard +{self.delay_minutes} min"
        if self.delay_minutes < 0:
            return f"🟢 En avance ({self.delay_minutes} min)"
        return "🟢 À l'heure"


@dataclass(frozen=True)
class CommuteStatus:
    direction: CommuteDirection
    query_time: datetime
    departures: list[TrainDeparture]
    general_disruptions: list[str] = field(default_factory=list)
