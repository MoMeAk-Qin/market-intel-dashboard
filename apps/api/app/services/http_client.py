from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

RETRY_STATUS = {429, 500, 502, 503, 504}


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    retries: int,
    backoff: float,
    logger: logging.Logger,
    **kwargs: Any,
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
