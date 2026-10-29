"""HTTP helper with exponential backoff for external APIs (Rules R2)."""

import asyncio
from typing import Any

import httpx

MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.0
MAX_RETRY_AFTER_SECONDS = 30.0
RETRYABLE_STATUS = frozenset({429, 502, 503, 504})

_sleep = asyncio.sleep


def _delay(response: httpx.Response | None, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After") if response is not None else None
    if retry_after and retry_after.isdigit():
        return min(float(retry_after), MAX_RETRY_AFTER_SECONDS)
    return float(BACKOFF_BASE_SECONDS * 2**attempt)


async def request_with_retry(
    client: httpx.AsyncClient, method: str, url: str, **kwargs: Any
) -> httpx.Response:
    """Send a request, retrying transient failures with exponential backoff.

    Retries network errors and HTTP 429/502/503/504 up to ``MAX_ATTEMPTS`` times.

    Raises:
        httpx.HTTPStatusError: Non-retryable status, or retries exhausted on a status.
        httpx.RequestError: Retries exhausted on a network error.
    """
    for attempt in range(MAX_ATTEMPTS):
        last_attempt = attempt == MAX_ATTEMPTS - 1
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.RequestError:
            if last_attempt:
                raise
            await _sleep(_delay(None, attempt))
            continue
        if response.status_code in RETRYABLE_STATUS and not last_attempt:
            await _sleep(_delay(response, attempt))
            continue
        response.raise_for_status()
        return response
    raise RuntimeError("unreachable")  # pragma: no cover
