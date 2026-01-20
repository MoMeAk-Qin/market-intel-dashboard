from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .models import Event


@dataclass
class InMemoryStore:
    events: list[Event] = field(default_factory=list)
    updated_at: datetime | None = None

    def replace_events(self, events: list[Event]) -> None:
        self.events = events
        self.updated_at = datetime.utcnow()
