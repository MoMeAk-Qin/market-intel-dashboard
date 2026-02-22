from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import math
from typing import cast

from ..config import AppConfig
from ..models import CorrelationMatrixResponse, CorrelationPreset, CorrelationWindowDays, QuoteSnapshot

DEFAULT_WINDOW: CorrelationWindowDays = 30


def build_correlation_matrix(
    *,
    quotes: dict[str, QuoteSnapshot],
    config: AppConfig,
    preset: CorrelationPreset,
    window_days: CorrelationWindowDays,
) -> CorrelationMatrixResponse:
    assets = list(resolve_preset_assets(config, preset))
    series_map: dict[str, list[float]] = {}
    fallback_assets: list[str] = []

    for asset in assets:
        quote = quotes.get(asset)
        if quote is None or quote.is_fallback or quote.source == "seed":
            fallback_assets.append(asset)
        series_map[asset] = _simulate_returns(asset, window_days, quote)

    matrix = [
        [
            _pearson(series_map[row_asset], series_map[col_asset])
            for col_asset in assets
        ]
        for row_asset in assets
    ]
    note = _build_note(fallback_assets)

    return CorrelationMatrixResponse(
        preset=preset,
        window_days=window_days,
        assets=assets,
        matrix=matrix,
        fallback_assets=fallback_assets,
        updated_at=datetime.now(UTC),
        note=note,
    )


def resolve_preset_assets(config: AppConfig, preset: CorrelationPreset) -> tuple[str, ...]:
    if preset == "A":
        return config.correlation_macro_core
    if preset == "B":
        return config.correlation_ai_supply_chain
    return config.correlation_cross_border_tech


def normalize_window_days(value: int, *, allowed: tuple[int, ...]) -> CorrelationWindowDays:
    if value in allowed and value in {7, 30, 90}:
        return cast(CorrelationWindowDays, value)
    return DEFAULT_WINDOW


def _simulate_returns(asset_id: str, days: int, quote: QuoteSnapshot | None) -> list[float]:
    phase_seed = _stable_int(asset_id) % 360
    phase = math.radians(phase_seed)
    bias = ((phase_seed % 37) - 18) / 1200
    quote_trend = (quote.change_pct or 0.0) / 100.0 if quote is not None else 0.0
    levels: list[float] = []
    for idx in range(days + 1):
        x = idx + 1
        wave = math.sin(x * 0.19 + phase) * 0.8 + math.cos(x * 0.07 + phase * 0.65) * 0.5
        drift = bias * x
        trend = quote_trend * (x / max(days, 1)) * 0.45
        micro_noise = ((_stable_int(f"{asset_id}:{x}") % 1000) / 1000 - 0.5) * 0.08
        levels.append(wave + drift + trend + micro_noise)
    returns = [levels[i + 1] - levels[i] for i in range(len(levels) - 1)]
    return returns


def _pearson(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or not x:
        return 0.0
    mean_x = sum(x) / len(x)
    mean_y = sum(y) / len(y)
    cov = sum((vx - mean_x) * (vy - mean_y) for vx, vy in zip(x, y, strict=False))
    var_x = sum((vx - mean_x) ** 2 for vx in x)
    var_y = sum((vy - mean_y) ** 2 for vy in y)
    denom = math.sqrt(var_x * var_y)
    if denom == 0:
        return 0.0
    corr = cov / denom
    return round(max(-1.0, min(1.0, corr)), 4)


def _build_note(fallback_assets: list[str]) -> str | None:
    if not fallback_assets:
        return None
    if "US02Y" in fallback_assets:
        return "US02Y 暂无实时行情，已回退为 seed 序列估算。"
    return f"部分资产缺少实时行情，已对 {len(fallback_assets)} 个资产使用 seed 序列估算。"


def _stable_int(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)
