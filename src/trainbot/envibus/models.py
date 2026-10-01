"""Data models for Envibus Line A bus departures."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class BusDeparture:
    """A single bus departure."""

    minutes_away: int
    estimated_time: datetime
    destination: str
    is_realtime: bool = True

    @property
    def formatted_time(self) -> str:
        """Formatted HH:MM string."""
        return self.estimated_time.strftime("%H:%M")

    @property
    def status_summary(self) -> str:
        """User-friendly time summary, e.g. 'Dans 9 min (20:45)'."""
        if self.minutes_away <= 0:
            return f"À l'approche ({self.formatted_time})"
        return f"Dans {self.minutes_away} min ({self.formatted_time})"


@dataclass(frozen=True)
class BusCommuteStatus:
    """Status container for bus departures at a given stop and direction."""

    line_name: str
    stop_name: str
    direction_name: str
    departures: list[BusDeparture] = field(default_factory=list)
    query_time: datetime = field(default_factory=datetime.now)
    is_live: bool = True

    @property
    def has_departures(self) -> bool:
        return bool(self.departures)
