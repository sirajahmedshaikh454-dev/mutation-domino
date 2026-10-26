from __future__ import annotations

import asyncio
import json
import random
from collections.abc import Iterable
from urllib.parse import urlsplit

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.errors import (
    RateLimited,
    StructureTooLarge,
    UpstreamError,
    UpstreamTimeout,
)

logger = get_logger(__name__)

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
JSON_CONTENT_TYPES = {"application/json", "application/problem+json", "text/json", ""}


class UpstreamStatusError(UpstreamError):
    def __init__(self, status_code: int, url: str) -> None:
        super().__init__(
            "The upstream service returned an error response.",
            details={"upstream_status": status_code},
        )
        self.status_code = status_code
        self.url = url


def validate_upstream_url(url: str, allowed_hosts: Iterable[str]) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https":
        raise UpstreamError("Upstream URL must use HTTPS.")
    if parsed.username or parsed.password:
        raise UpstreamError("Upstream URL must not contain credentials.")
    host = (parsed.hostname or "").lower()
    allowed = {h.lower() for h in allowed_hosts}
    if host not in allowed:
        raise UpstreamError("Upstream host is not on the allowlist.", details={"host": host})
    if parsed.port not in (None, 443):
        raise UpstreamError("Upstream URL must use the standard HTTPS port.")
    return url


class BoundedHttpClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        retries: int = 2,
    ) -> None:
        self._settings = settings
        self._retries = max(0, retries)
        self._client = httpx.AsyncClient(
            follow_redirects=False,
            transport=transport,
            timeout=httpx.Timeout(
                connect=settings.connect_timeout_seconds,
                read=settings.read_timeout_seconds,
                write=settings.read_timeout_seconds,
                pool=settings.connect_timeout_seconds,
            ),
            headers={"User-Agent": settings.user_agent},
        )

    async def __aenter__(self) -> BoundedHttpClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        url: str,
        *,
        allowed_hosts: Iterable[str],
        accept: str,
        max_bytes: int,
        large_error: str,
    ) -> tuple[bytes, str, int]:
        validate_upstream_url(url, allowed_hosts)
        attempt = 0
        while True:
            attempt += 1
            try:
                async with self._client.stream(
                    "GET",
                    url,
                    headers={"Accept": accept},
                ) as response:
                    if response.status_code in REDIRECT_STATUS_CODES:
                        raise UpstreamError("Upstream redirected the request; redirects are not followed.")
                    if response.status_code in TRANSIENT_STATUS_CODES and attempt <= self._retries:
                        delay = min(2.0, 0.25 * attempt) + random.uniform(0, 0.1)
                        logger.warning(
                            "Transient upstream status %s for %s; retrying in %.2fs",
                            response.status_code,
                            urlsplit(url).path,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    if response.status_code == 404:
                        raise UpstreamStatusError(404, url)
                    if response.status_code == 429:
                        raise RateLimited("The upstream service is rate limiting requests. Try again later.")
                    if response.status_code >= 400:
                        raise UpstreamStatusError(response.status_code, url)
                    content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
                    length_header = response.headers.get("content-length")
                    if length_header and length_header.isdigit() and int(length_header) > max_bytes:
                        self._raise_too_large(large_error, max_bytes, int(length_header))
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > max_bytes:
                            self._raise_too_large(large_error, max_bytes, total)
                        chunks.append(chunk)
                    return b"".join(chunks), content_type, response.status_code
            except httpx.TimeoutException as exc:
                if attempt <= self._retries:
                    await asyncio.sleep(0.25 * attempt)
                    continue
                raise UpstreamTimeout("The upstream service did not respond in time.") from exc
            except httpx.HTTPError as exc:
                if attempt <= self._retries:
                    await asyncio.sleep(0.25 * attempt)
                    continue
                raise UpstreamError("The upstream service could not be reached.") from exc

    @staticmethod
    def _raise_too_large(large_error: str, max_bytes: int, content_length: int) -> None:
        if large_error == "structure":
            raise StructureTooLarge(
                "The upstream response is larger than the configured limit.",
                details={"content_length": content_length, "limit": max_bytes},
            )
        raise UpstreamError(
            "The upstream metadata response is larger than the configured limit.",
            details={"content_length": content_length, "limit": max_bytes},
        )

    async def get_bytes(
        self,
        url: str,
        *,
        allowed_hosts: Iterable[str],
        accept: str = "application/octet-stream",
        max_bytes: int | None = None,
    ) -> tuple[bytes, str]:
        limit = max_bytes or self._settings.max_structure_bytes
        payload, content_type, _ = await self._request(
            url,
            allowed_hosts=allowed_hosts,
            accept=accept,
            max_bytes=limit,
            large_error="structure",
        )
        return payload, content_type

    async def get_json(
        self,
        url: str,
        *,
        allowed_hosts: Iterable[str],
        accept: str = "application/json",
    ) -> object:
        payload, content_type, _ = await self._request(
            url,
            allowed_hosts=allowed_hosts,
            accept=accept,
            max_bytes=self._settings.max_metadata_bytes,
            large_error="metadata",
        )
        if content_type not in JSON_CONTENT_TYPES:
            raise UpstreamError(
                "The upstream service returned an unexpected content type.",
                details={"content_type": content_type},
            )
        try:
            return json.loads(payload)
        except (UnicodeDecodeError, ValueError) as exc:
            raise UpstreamError("The upstream service returned malformed JSON.") from exc
