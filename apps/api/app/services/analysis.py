from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from threading import Lock
import time
import re

from openai import OpenAI

from ..config import AppConfig
from ..models import AnalysisRequest, AnalysisResponse, AnalysisUsage, EventEvidence
from .vector_store import EmbeddingsUnavailable, VectorStore, VectorStoreDisabled

_REQUIRED_SECTIONS: tuple[str, ...] = ("【结论】", "【影响】", "【风险】", "【关注点】")
_REF_PATTERN = re.compile(r"\[(\d+)\]")


@dataclass(frozen=True)
class _CacheEntry:
    response: AnalysisResponse
    expires_at: float


_ANALYSIS_CACHE: dict[str, _CacheEntry] = {}
_ANALYSIS_CACHE_LOCK = Lock()


def analyze_financial_sources(
    payload: AnalysisRequest,
    config: AppConfig,
    vector_store: VectorStore | None = None,
) -> AnalysisResponse:
    if not payload.question.strip():
        raise ValueError("question is required")
    if not config.dashscope_api_key:
        raise ValueError("DASHSCOPE_API_KEY is required for Qwen analysis")
    cache_ttl = max(config.analysis_cache_ttl_seconds, 0)
    cache_key = _build_cache_key(payload, config)
    if cache_ttl > 0:
        cached = _get_cached_response(cache_key)
        if cached is not None:
            return cached

    retrieved: list[EventEvidence] = []
    if payload.use_retrieval and vector_store is not None:
        try:
            hits = vector_store.query(payload.question, top_k=payload.top_k)
            retrieved = [hit.evidence for hit in hits]
        except (EmbeddingsUnavailable, VectorStoreDisabled) as exc:
            # PC 端允许“无向量检索”降级运行。
            retrieved = []
        except Exception:
            retrieved = []

    client = OpenAI(
        api_key=config.dashscope_api_key,
        base_url=config.qwen_base_url,
    )

    system_parts = [
        "你是金融信源分析助手。",
        "你必须严格按固定模板输出，不要增加或删除一级标题。",
        "固定模板如下：",
        "【结论】",
        "【影响】",
        "【风险】",
        "【关注点】",
        "引用信源请用方括号编号（例如：[1]、[2]）。",
        "如果证据不足，也要在【风险】明确说明，并保持模板完整。",
    ]
    if payload.sources:
        numbered = [f"[{idx + 1}] {source}" for idx, source in enumerate(payload.sources)]
        system_parts.append("用户提供的来源链接：\n" + "\n".join(numbered))

    if retrieved:
        base = len(payload.sources)
        lines: list[str] = []
        for idx, ev in enumerate(retrieved):
            lines.append(
                "\n".join(
                    [
                        f"[{base + idx + 1}] {ev.title}",
                        f"URL: {ev.source_url}",
                        f"发布时间: {ev.published_at.isoformat()}",
                        f"摘录: {ev.excerpt}",
                    ]
                )
            )
        system_parts.append("系统检索到的信源摘录：\n" + "\n\n".join(lines))

    user_parts = [payload.question.strip()]
    if payload.context:
        user_parts.append("Context:\n" + payload.context.strip())

    response = client.chat.completions.create(
        model=config.qwen_model,
        messages=[
            {"role": "system", "content": "\n".join(system_parts)},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ],
        temperature=config.qwen_temperature,
        max_tokens=config.qwen_max_tokens,
    )

    choice = response.choices[0]
    content = choice.message.content or ""
    source_count = len(payload.sources) + len(retrieved)
    final_answer = _enforce_answer_template(
        content,
        source_count=source_count,
        question=payload.question.strip(),
        retrieved=retrieved,
    )
    usage = response.usage
    parsed_usage = None
    if usage:
        parsed_usage = AnalysisUsage(
            prompt_tokens=usage.prompt_tokens or 0,
            completion_tokens=usage.completion_tokens or 0,
            total_tokens=usage.total_tokens or 0,
        )
    result = AnalysisResponse(
        answer=final_answer,
        model=config.qwen_model,
        usage=parsed_usage,
        sources=retrieved,
    )
    if cache_ttl > 0:
        _set_cached_response(cache_key, result, ttl_seconds=cache_ttl)
    return result


def _build_cache_key(payload: AnalysisRequest, config: AppConfig) -> str:
    key_data = {
        "question": payload.question.strip(),
        "context": (payload.context or "").strip(),
        "sources": payload.sources,
        "use_retrieval": payload.use_retrieval,
        "top_k": payload.top_k,
        "model": config.qwen_model,
        "temperature": config.qwen_temperature,
        "max_tokens": config.qwen_max_tokens,
    }
    key_text = json.dumps(key_data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(key_text.encode("utf-8")).hexdigest()


def _get_cached_response(cache_key: str) -> AnalysisResponse | None:
    now = time.time()
    with _ANALYSIS_CACHE_LOCK:
        entry = _ANALYSIS_CACHE.get(cache_key)
        if entry is None:
            return None
        if entry.expires_at <= now:
            _ANALYSIS_CACHE.pop(cache_key, None)
            return None
        return entry.response.model_copy(deep=True)


def _set_cached_response(cache_key: str, response: AnalysisResponse, *, ttl_seconds: int) -> None:
    with _ANALYSIS_CACHE_LOCK:
        _ANALYSIS_CACHE[cache_key] = _CacheEntry(
            response=response.model_copy(deep=True),
            expires_at=time.time() + ttl_seconds,
        )


def _enforce_answer_template(
    answer: str,
    *,
    source_count: int,
    question: str,
    retrieved: list[EventEvidence],
) -> str:
    content = answer.strip()
    if _is_valid_template(content, source_count=source_count):
        return content
    return _build_fallback_answer(
        question=question,
        source_count=source_count,
        retrieved=retrieved,
    )


def _is_valid_template(answer: str, *, source_count: int) -> bool:
    if not answer:
        return False
    for section in _REQUIRED_SECTIONS:
        if section not in answer:
            return False
    if source_count <= 0:
        return True
    refs = [int(item) for item in _REF_PATTERN.findall(answer)]
    if not refs:
        return False
    return all(1 <= ref <= source_count for ref in refs)


def _build_fallback_answer(
    *,
    question: str,
    source_count: int,
    retrieved: list[EventEvidence],
) -> str:
    refs = _render_refs(source_count)
    if retrieved:
        leading = retrieved[0].title
        conclusion = f"围绕“{question}”，当前最相关线索来自：{leading}。{refs}".strip()
    else:
        conclusion = f"围绕“{question}”，当前可用证据有限，结论仅作参考。{refs}".strip()
    impact = f"短期影响主要体现在风险偏好与定价预期变化上，需结合后续发布继续确认。{refs}".strip()
    risk = (
        f"当前回答触发了结构化降级生成，建议补充更多高质量来源以提升结论稳定性。{refs}".strip()
        if source_count > 0
        else "当前无可编号证据，需先补充来源后再做高置信度判断。"
    )
    watchpoints = f"建议持续跟踪后续公告、宏观数据与价格联动信号，并进行滚动复核。{refs}".strip()
    return "\n".join(
        [
            "【结论】",
            conclusion,
            "【影响】",
            impact,
            "【风险】",
            risk,
            "【关注点】",
            watchpoints,
        ]
    )


def _render_refs(source_count: int) -> str:
    if source_count <= 0:
        return ""
    count = min(source_count, 3)
    return "".join(f"[{idx}]" for idx in range(1, count + 1))
