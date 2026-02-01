from __future__ import annotations

from openai import OpenAI

from ..config import AppConfig
from ..models import AnalysisRequest, AnalysisResponse, AnalysisUsage, EventEvidence
from .vector_store import EmbeddingsUnavailable, VectorStore, VectorStoreDisabled


def analyze_financial_sources(
    payload: AnalysisRequest,
    config: AppConfig,
    vector_store: VectorStore | None = None,
) -> AnalysisResponse:
    if not payload.question.strip():
        raise ValueError("question is required")
    if not config.dashscope_api_key:
        raise ValueError("DASHSCOPE_API_KEY is required for Qwen analysis")

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
        "用中文输出，尽量结构化（要点/结论/风险/关注点）。",
        "如引用信源，请用方括号编号标注（例如：[1]）。",
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
    usage = response.usage
    parsed_usage = None
    if usage:
        parsed_usage = AnalysisUsage(
            prompt_tokens=usage.prompt_tokens or 0,
            completion_tokens=usage.completion_tokens or 0,
            total_tokens=usage.total_tokens or 0,
        )
    return AnalysisResponse(
        answer=content,
        model=config.qwen_model,
        usage=parsed_usage,
        sources=retrieved,
    )
