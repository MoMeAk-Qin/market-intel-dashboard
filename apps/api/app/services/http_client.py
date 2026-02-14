from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, TypedDict, Unpack

import httpx

RETRY_STATUS = {429, 500, 502, 503, 504}


class RequestOptions(TypedDict, total=False):
    params: httpx.QueryParamTypes
    headers: httpx.HeaderTypes
    cookies: httpx.CookieTypes
    content: httpx.RequestContent | None
    data: httpx.RequestData | None
    files: httpx.RequestFiles | None
    json: Any
    timeout: httpx.TimeoutTypes
    extensions: dict[str, Any]


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    retries: int,
    backoff: float,
    logger: logging.Logger,
    **kwargs: Unpack[RequestOptions],
) -> httpx.Response:
    attempt = 0
    while True:
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code in RETRY_STATUS:
                raise httpx.HTTPStatusError(
                    f"Retryable status {response.status_code}",
                    request=response.request,
                    response=response,
                )
            return response
        except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
            if attempt >= retries:
                logger.error(
                    "request_failed method=%s url=%s attempts=%s error=%s",
                    method,
                    url,
                    attempt + 1,
                    exc,
                )
                raise
            wait = backoff * (2**attempt) + random.random() * 0.1
            logger.warning(
                "request_retry method=%s url=%s attempt=%s wait=%.2fs error=%s",
                method,
                url,
                attempt + 1,
                wait,
                exc,
            )
            await asyncio.sleep(wait)
            attempt += 1
