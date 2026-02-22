from __future__ import annotations

from datetime import UTC, datetime, timedelta
import re
from typing import Iterable

from ..config import AppConfig
from ..models import Event, HeatLevel, HeatSourceType, QuoteSnapshot, TechHeatItem, TechHeatmapResponse

_UNLISTED_ALIASES: dict[str, tuple[str, ...]] = {
    "MINIMAX": ("minimax", "mini max", "稀宇科技", "海螺ai"),
}


def build_tech_heatmap(
    *,
    events: Iterable[Event],
    quotes: dict[str, QuoteSnapshot],
    config: AppConfig,
    limit: int = 24,
) -> TechHeatmapResponse:
    watchlist = _build_watchlist(config)
    recent_cutoff = datetime.now(UTC) - timedelta(days=7)
    event_list = list(events)
    items: list[TechHeatItem] = []

    for asset_id in watchlist:
        matched_events = [event for event in event_list if _event_matches_asset(event, asset_id)]
        recent_events = [event for event in matched_events if _to_utc(event.event_time) >= recent_cutoff]
        mentions = len(recent_events)
        avg_impact = (
            sum(event.impact for event in recent_events) / mentions
            if mentions > 0
            else 0.0
        )

        quote = quotes.get(asset_id)
        change_pct = quote.change_pct if quote is not None else None
        score = _calc_heat_score(
            avg_impact=avg_impact,
            mentions=mentions,
            change_pct=change_pct,
        )
        level = _score_level(score, threshold=config.tech_heat_alert_threshold)
        source_type = _resolve_source_type(matched_events, quote)

        items.append(
            TechHeatItem(
                asset_id=asset_id,
                market=_asset_market(asset_id),
                latest_price=quote.price if quote is not None else None,
                change_pct=change_pct,
                mentions_7d=mentions,
                avg_impact=round(avg_impact, 2),
                heat_score=score,
                level=level,
                source_type=source_type,
            )
        )

    items.sort(key=lambda item: (item.heat_score, item.mentions_7d), reverse=True)
    return TechHeatmapResponse(
        generated_at=datetime.now(UTC),
        threshold=config.tech_heat_alert_threshold,
        items=items[: max(1, limit)],
    )


def _build_watchlist(config: AppConfig) -> list[str]:
    assets: list[str] = []
    for group in (
        config.tech_watchlist_us,
        config.tech_watchlist_hk,
        config.tech_watchlist_unlisted,
    ):
        for item in group:
            normalized = item.strip().upper()
            if not normalized or normalized in assets:
                continue
            assets.append(normalized)
    return assets


def _event_matches_asset(event: Event, asset_id: str) -> bool:
    asset_upper = asset_id.upper()
    if asset_upper in event.tickers or asset_upper in event.instruments:
        return True
    aliases = _UNLISTED_ALIASES.get(asset_upper)
    if not aliases:
        return False
    haystack = _normalize_text(
        " ".join(
            [
                event.headline,
                event.summary,
                event.publisher,
                " ".join(event.tickers),
                " ".join(event.instruments),
            ]
        )
    )
    return any(_normalize_text(alias) in haystack for alias in aliases)


def _resolve_source_type(events: list[Event], quote: QuoteSnapshot | None) -> HeatSourceType:
    event_origins = {event.data_origin for event in events}
    quote_origin = "live" if quote and not quote.is_fallback and quote.source != "seed" else "seed"

    if not event_origins:
        return "live" if quote_origin == "live" else "seed"
    if len(event_origins) > 1:
        return "mixed"
    event_origin = next(iter(event_origins))
    if event_origin == quote_origin:
        return "live" if event_origin == "live" else "seed"
    return "mixed"


def _score_level(score: float, threshold: float) -> HeatLevel:
    medium_threshold = threshold * 0.65
    if score >= threshold:
        return "high"
    if score >= medium_threshold:
        return "medium"
    return "low"


def _calc_heat_score(*, avg_impact: float, mentions: int, change_pct: float | None) -> float:
    mention_score = min(mentions * 8.0, 32.0)
    impact_score = min(avg_impact * 0.55, 55.0)
    quote_score = min(abs(change_pct or 0.0) * 3.2, 23.0)
    total = mention_score + impact_score + quote_score
    return round(max(0.0, min(100.0, total)), 2)


def _asset_market(asset_id: str) -> str:
    if asset_id.endswith(".HK"):
        return "HK"
    if asset_id in {"DXY", "EURUSD", "USDJPY", "USDCNH"}:
        return "FX"
    if re.match(r"^US\d+Y$", asset_id):
        return "RATES"
    if asset_id in {"XAUUSD", "XAGUSD"}:
        return "METALS"
    if asset_id in _UNLISTED_ALIASES:
        return "UNLISTED"
    return "US"


def _normalize_text(value: str) -> str:
    return re.sub(r"[\s\W_]+", "", value.casefold(), flags=re.UNICODE)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
