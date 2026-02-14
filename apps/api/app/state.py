from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .models import Event, QuoteSnapshot, RefreshReport


@dataclass
class InMemoryStore:
    events: list[Event] = field(default_factory=list)
    quotes: dict[str, QuoteSnapshot] = field(default_factory=dict)
    updated_at: datetime | None = None
    quotes_updated_at: datetime | None = None
    last_refresh_report: RefreshReport | None = None
    last_refresh_error: str | None = None

    def replace_events(self, events: list[Event]) -> None:
        self.events = events
        self.updated_at = datetime.now(UTC)

    def replace_quotes(self, quotes: dict[str, QuoteSnapshot]) -> None:
        self.quotes = quotes
        self.quotes_updated_at = datetime.now(UTC)

    def upsert_quote(self, quote: QuoteSnapshot) -> None:
        self.quotes[quote.asset_id] = quote
        self.quotes_updated_at = datetime.now(UTC)

    def set_refresh_report(self, report: RefreshReport) -> None:
        self.last_refresh_report = report
        self.last_refresh_error = None

    def set_refresh_error(self, error: str) -> None:
        self.last_refresh_error = error
