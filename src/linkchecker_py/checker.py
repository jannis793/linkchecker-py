from __future__ import annotations

import asyncio
import fnmatch
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import unquote, urldefrag, urljoin, urlparse, urlsplit

import httpx

from linkchecker_py._version import __version__
from linkchecker_py.cache import ResultCache
from linkchecker_py.extractors import extract_links_from_file, extract_links_from_text
from linkchecker_py.models import Link, LinkResult, LinkStatus
from linkchecker_py.robots import RobotsCache

TRANSIENT_STATUS_CODES = frozenset({429, 502, 503, 504})


@dataclass
class CheckOptions:
    root: Path = Path.cwd()
    exclude: list[str] = field(default_factory=list)
    timeout: float = 10.0
    concurrency: int = 20
    rate_limit: float = 0.0
    user_agent: str = f"linkchecker-py/{__version__}"
    cache: bool = False
    cache_ttl: int = 3600
    respect_robots: bool = True
    retries: int = 2
    retry_backoff: float = 0.25
    retry_max_delay: float = 60.0


@dataclass(frozen=True)
class RemoteResource:
    response: httpx.Response | None = None
    error: httpx.HTTPError | None = None
    blocked_by_robots: bool = False


class LinkChecker:
    def __init__(self, options: CheckOptions, client: httpx.AsyncClient | None = None) -> None:
        self.options = options
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(
            timeout=options.timeout,
            follow_redirects=True,
            headers={"User-Agent": options.user_agent},
        )
        self._semaphore = asyncio.Semaphore(options.concurrency)
        self._cache = ResultCache(ttl_seconds=options.cache_ttl) if options.cache else None
        self._robots = RobotsCache(options.user_agent)
        self._pace_locks: dict[str, asyncio.Lock] = {}
        self._last_requests: dict[str, float] = {}
        self._resource_tasks: dict[str, asyncio.Task[RemoteResource]] = {}
        self._resource_lock = asyncio.Lock()
        self._result_tasks: dict[tuple[str, str | None], asyncio.Task[LinkResult]] = {}
        self._result_lock = asyncio.Lock()

    async def aclose(self) -> None:
        if self._cache:
            self._cache.save()
        if self._owns_client:
            await self.client.aclose()

    async def check_urls(
        self,
        urls: list[str],
        source: Path | None = None,
        lines: list[int | None] | None = None,
    ) -> list[LinkResult]:
        source_lines = lines or [None] * len(urls)
        if len(source_lines) != len(urls):
            raise ValueError("lines must have the same length as urls")
        return await asyncio.gather(
            *(
                self.check_url(url, source=source, line=line)
                for url, line in zip(urls, source_lines, strict=True)
            )
        )

    async def check_links(self, links: Iterable[Link]) -> list[LinkResult]:
        return await asyncio.gather(
            *(self.check_url(link.url, source=link.source, line=link.line) for link in links)
        )

    async def check_url(
        self,
        url: str,
        source: Path | None = None,
        line: int | None = None,
    ) -> LinkResult:
        parsed = urlparse(url)
        source_key = None if parsed.scheme in {"http", "https"} else _source(source)
        key = (url, source_key)
        async with self._result_lock:
            task = self._result_tasks.get(key)
            if task is None:
                task = asyncio.create_task(self._check_url_once(url, source))
                self._result_tasks[key] = task
        result = await task
        return replace(result, source=_source(source), line=line)

    async def _check_url_once(self, url: str, source: Path | None) -> LinkResult:
        if self._is_excluded(url):
            return LinkResult(url=url, status=LinkStatus.SKIPPED, message="excluded")
        parsed = urlparse(url)
        if parsed.scheme in {"mailto", "tel", "javascript", "data"}:
            return LinkResult(
                url=url,
                status=LinkStatus.SKIPPED,
                message="unsupported scheme",
            )
        if parsed.scheme in {"http", "https"}:
            return await self._check_remote(url, None, None)
        return self._check_local(url, source, None)

    async def get_response(self, url: str) -> httpx.Response | None:
        """Return the run-local response used to check a remote URL, if available."""
        base_url = urldefrag(url)[0]
        resource = await self._get_resource(base_url)
        return resource.response

    async def _check_remote(
        self,
        url: str,
        source: Path | None,
        line: int | None,
    ) -> LinkResult:
        base_url, fragment = urldefrag(url)
        fragment = unquote(fragment)
        cached = self._cache.get(url) if self._cache else None
        if cached:
            return replace(cached, url=url, source=_source(source), line=line)

        resource = await self._get_resource(base_url)
        if resource.blocked_by_robots:
            result = LinkResult(
                url=url,
                status=LinkStatus.SKIPPED,
                source=_source(source),
                line=line,
                message="blocked by robots.txt",
            )
        elif resource.error is not None:
            result = LinkResult(
                url=url,
                status=LinkStatus.BROKEN,
                source=_source(source),
                line=line,
                message=str(resource.error),
            )
        else:
            response = resource.response
            assert response is not None
            if response.status_code >= 400:
                result = LinkResult(
                    url=url,
                    status=LinkStatus.BROKEN,
                    source=_source(source),
                    line=line,
                    status_code=response.status_code,
                )
            elif fragment and not _html_has_anchor(response.text, fragment):
                result = LinkResult(
                    url=url,
                    status=LinkStatus.BROKEN,
                    source=_source(source),
                    line=line,
                    status_code=response.status_code,
                    message=f"missing anchor #{fragment}",
                )
            else:
                result = LinkResult(
                    url=url,
                    status=LinkStatus.OK,
                    source=_source(source),
                    line=line,
                    status_code=response.status_code,
                )
        if self._cache:
            self._cache.set(url, replace(result, source=None, line=None))
        return result

    async def _get_resource(self, base_url: str) -> RemoteResource:
        async with self._resource_lock:
            task = self._resource_tasks.get(base_url)
            if task is None:
                task = asyncio.create_task(self._fetch_resource(base_url))
                self._resource_tasks[base_url] = task
        return await task

    async def _fetch_resource(self, base_url: str) -> RemoteResource:
        if self.options.respect_robots and not await self._robots.can_fetch(
            self._request, base_url
        ):
            return RemoteResource(blocked_by_robots=True)
        try:
            response = await self._request(base_url)
        except httpx.HTTPError as exc:
            return RemoteResource(error=exc)
        return RemoteResource(response=response)

    async def _request(self, url: str) -> httpx.Response:
        for attempt in range(self.options.retries + 1):
            try:
                async with self._semaphore:
                    await self._pace(url)
                    response = await self.client.get(url)
            except httpx.TransportError:
                if attempt >= self.options.retries:
                    raise
                await asyncio.sleep(self._retry_delay(None, attempt))
                continue
            if (
                response.status_code not in TRANSIENT_STATUS_CODES
                or attempt >= self.options.retries
            ):
                return response
            await asyncio.sleep(self._retry_delay(response, attempt))
        raise AssertionError("retry loop did not return")

    def _check_local(
        self,
        url: str,
        source: Path | None,
        line: int | None,
    ) -> LinkResult:
        parsed = urlsplit(url)
        raw_path = unquote(parsed.path)
        fragment = unquote(parsed.fragment)
        metadata = {"source": _source(source), "line": line}
        if not raw_path and source:
            target = source.resolve()
        elif raw_path.startswith("/"):
            target = (self.options.root / raw_path.lstrip("/")).resolve()
        else:
            base = source.parent if source else self.options.root
            target = (base / raw_path).resolve()
        if not _is_within(target, self.options.root.resolve()):
            return LinkResult(
                url=url,
                status=LinkStatus.SKIPPED,
                message="outside root",
                **metadata,
            )
        if not target.exists():
            return LinkResult(
                url=url,
                status=LinkStatus.BROKEN,
                message="file not found",
                **metadata,
            )
        if target.is_dir():
            return LinkResult(
                url=url,
                status=LinkStatus.UNKNOWN if fragment else LinkStatus.OK,
                message="cannot validate anchor on directory" if fragment else None,
                **metadata,
            )
        if fragment:
            try:
                document = extract_links_from_file(target)
            except (OSError, UnicodeDecodeError):
                return LinkResult(
                    url=url,
                    status=LinkStatus.UNKNOWN,
                    message="cannot read anchors",
                    **metadata,
                )
            if fragment not in document.anchors:
                return LinkResult(
                    url=url,
                    status=LinkStatus.BROKEN,
                    message=f"missing anchor #{fragment}",
                    **metadata,
                )
        return LinkResult(url=url, status=LinkStatus.OK, **metadata)

    async def _pace(self, url: str) -> None:
        if self.options.rate_limit <= 0:
            return
        parsed = urlparse(url)
        host = (parsed.hostname or parsed.netloc).lower()
        lock = self._pace_locks.setdefault(host, asyncio.Lock())
        interval = 1 / self.options.rate_limit
        async with lock:
            now = asyncio.get_running_loop().time()
            wait_for = self._last_requests.get(host, 0.0) + interval - now
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._last_requests[host] = asyncio.get_running_loop().time()

    def _retry_delay(self, response: httpx.Response | None, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After") if response is not None else None
        if retry_after:
            delay: float | None
            try:
                delay = float(retry_after)
            except ValueError:
                try:
                    parsed = parsedate_to_datetime(retry_after)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    delay = (parsed - datetime.now(timezone.utc)).total_seconds()
                except (TypeError, ValueError, OverflowError):
                    delay = None
            if delay is not None:
                return max(0.0, min(delay, self.options.retry_max_delay))
        return min(self.options.retry_backoff * (2**attempt), self.options.retry_max_delay)

    def _is_excluded(self, url: str) -> bool:
        return any(fnmatch.fnmatch(url, pattern) for pattern in self.options.exclude)


def resolve_url(base_url: str, href: str) -> str:
    return urljoin(base_url, href)


def extract_remote_links(html: str, url: str) -> list[str]:
    links, _anchors = extract_links_from_text(html, url)
    return [resolve_url(url, link) for link in links]


def _html_has_anchor(html: str, fragment: str) -> bool:
    _links, anchors = extract_links_from_text(html, "")
    return fragment in anchors


def _source(source: Path | None) -> str | None:
    return str(source) if source else None


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
