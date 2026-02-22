from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Iterable

from ..config import AppConfig
from ..models import (
    CausalAnalyzeRequest,
    CausalAnalyzeResponse,
    CausalNode,
    Event,
    EventEvidence,
    HeatSourceType,
    Market,
)
from .correlation_engine import resolve_preset_assets


def analyze_causal_chain(
    *,
    events: Iterable[Event],
    payload: CausalAnalyzeRequest,
    config: AppConfig,
) -> CausalAnalyzeResponse:
    event_list = list(events)
    root = _select_root_event(event_list, payload)
    if root is None:
        return CausalAnalyzeResponse(
            event_id=None,
            source_type="seed",
            summary="当前暂无可用于因果链分析的事件。",
            nodes=[],
            generated_at=datetime.now(UTC),
        )

    followups = _find_followups(event_list, root)
    nodes = _build_nodes(root=root, followups=followups, payload=payload, config=config)
    source_type = _resolve_source_type([root, *followups])
    summary = (
        f"以事件“{root.headline}”为起点，构建 {len(nodes)} 层传导链，"
        f"当前判定来源为 {source_type}。"
    )
    return CausalAnalyzeResponse(
        event_id=root.event_id,
        source_type=source_type,
        summary=summary,
        nodes=nodes,
        generated_at=datetime.now(UTC),
    )


def _select_root_event(events: list[Event], payload: CausalAnalyzeRequest) -> Event | None:
    if payload.event_id:
        for event in events:
            if event.event_id == payload.event_id:
                return event
    if payload.query:
        keyword = payload.query.strip().lower()
        filtered = [
            event
            for event in events
            if keyword in f"{event.headline} {event.summary} {event.publisher}".lower()
        ]
        if filtered:
            filtered.sort(key=lambda item: (item.impact, _to_utc(item.event_time)), reverse=True)
            return filtered[0]
    if not events:
        return None
    ranked = sorted(events, key=lambda item: (item.impact, _to_utc(item.event_time)), reverse=True)
    return ranked[0]


def _find_followups(events: list[Event], root: Event) -> list[Event]:
    root_time = _to_utc(root.event_time)
    candidates = [
        event
        for event in events
        if event.event_id != root.event_id
        and abs((_to_utc(event.event_time) - root_time).total_seconds()) <= timedelta(hours=72).total_seconds()
        and (
            bool(set(event.markets) & set(root.markets))
            or bool(set(event.tickers) & set(root.tickers))
            or bool(set(event.sectors) & set(root.sectors))
        )
    ]
    candidates.sort(key=lambda item: (item.impact, _to_utc(item.event_time)), reverse=True)
    return candidates[:3]


def _build_nodes(
    *,
    root: Event,
    followups: list[Event],
    payload: CausalAnalyzeRequest,
    config: AppConfig,
) -> list[CausalNode]:
    nodes: list[CausalNode] = [
        CausalNode(
            level=0,
            label="起点事件",
            detail=f"{root.publisher}：{root.headline}。{root.summary}",
            related_assets=_unique_assets([*root.tickers, *root.instruments]),
            confidence=round(root.confidence, 2),
            evidence=root.evidence[:2],
        )
    ]

    if payload.max_depth >= 2:
        first_chain = root.impact_chain[0] if root.impact_chain else "风险偏好变化将先反映在相关资产估值重定价。"
        nodes.append(
            CausalNode(
                level=1,
                label="一级传导",
                detail=first_chain,
                related_assets=_map_assets_from_markets(root.markets, config),
                confidence=round(min(0.98, root.confidence * 0.92), 2),
                evidence=root.evidence[:2],
            )
        )

    if payload.max_depth >= 3:
        if followups:
            detail = "；".join(f"{item.headline} (impact {item.impact})" for item in followups[:2])
            evidence: list[EventEvidence] = [
                item.evidence[0] for item in followups if item.evidence
            ][:2]
            followup_confidence = sum(item.confidence for item in followups) / len(followups)
            related_assets = _unique_assets(
                [asset for item in followups for asset in [*item.tickers, *item.instruments]]
            )
        else:
            detail = "尚未检索到同窗口强相关后续事件，二级传导仍在形成。"
            evidence = root.evidence[:1]
            followup_confidence = root.confidence * 0.75
            related_assets = _map_assets_from_markets(root.markets, config)[:4]
        nodes.append(
            CausalNode(
                level=2,
                label="二级联动",
                detail=detail,
                related_assets=related_assets,
                confidence=round(max(0.35, min(0.95, followup_confidence)), 2),
                evidence=evidence,
            )
        )

    if payload.max_depth >= 4:
        risk_detail = (
            "当前事件偏负面，需优先跟踪风险资产回撤与避险资产联动。"
            if root.stance == "negative"
            else "当前事件偏中性/正面，需关注后续兑现节奏与预期差。"
        )
        nodes.append(
            CausalNode(
                level=3,
                label="风险与观察",
                detail=risk_detail,
                related_assets=list(resolve_preset_assets(config, "B"))[:5],
                confidence=0.64,
                evidence=root.evidence[:1],
            )
        )

    if payload.max_depth >= 5:
        nodes.append(
            CausalNode(
                level=4,
                label="执行建议",
                detail="建议结合 7/30/90 天相关矩阵交叉验证，再决定是否提升仓位暴露。",
                related_assets=list(resolve_preset_assets(config, "C"))[:5],
                confidence=0.58,
                evidence=root.evidence[:1],
            )
        )

    return nodes[: payload.max_depth]


def _map_assets_from_markets(markets: list[Market], config: AppConfig) -> list[str]:
    mapped: list[str] = []
    for market in markets:
        if market == "US":
            mapped.extend(config.tech_watchlist_us[:3])
        elif market == "HK":
            mapped.extend(config.tech_watchlist_hk[:2])
        elif market == "RATES":
            mapped.extend(("US10Y", "US02Y"))
        elif market == "FX":
            mapped.extend(("DXY", "EURUSD"))
        elif market == "METALS":
            mapped.append("XAUUSD")
    return _unique_assets(mapped)


def _resolve_source_type(events: list[Event]) -> HeatSourceType:
    origins = {event.data_origin for event in events}
    if origins == {"live"}:
        return "live"
    if origins == {"seed"}:
        return "seed"
    return "mixed"


def _unique_assets(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for item in values:
        normalized = item.strip().upper()
        if not normalized or normalized in deduped:
            continue
        deduped.append(normalized)
    return deduped


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
