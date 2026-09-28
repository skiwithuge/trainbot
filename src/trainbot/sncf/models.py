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
        return "stop_area:OCE:SA:87757674" if self == CommuteDirection.ANTIBES_TO_NICE else "stop_area:OCE:SA:87756056"

    @property
    def destination_id(self) -> str:
        return "stop_area:OCE:SA:87756056" if self == CommuteDirection.ANTIBES_TO_NICE else "stop_area:OCE:SA:87757674"

    @property
    def reverse(self) -> CommuteDirection:
        return (
            CommuteDirection.NICE_TO_ANTIBES
            if self == CommuteDirection.ANTIBES_TO_NICE
            else CommuteDirection.ANTIBES_TO_NICE
        )


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
