from __future__ import annotations

import asyncio
import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

import httpx

from linkchecker_py.cache import ResultCache
from linkchecker_py.extractors import extract_links_from_file, extract_links_from_text
from linkchecker_py.models import LinkResult, LinkStatus
from linkchecker_py.robots import RobotsCache


@dataclass
class CheckOptions:
    root: Path = Path.cwd()
    exclude: list[str] = field(default_factory=list)
    timeout: float = 10.0
    concurrency: int = 20
    rate_limit: float = 0.0
    user_agent: str = "linkchecker-py/0.1"
    cache: bool = False
    cache_ttl: int = 3600
    respect_robots: bool = True


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
        self._last_request = 0.0

    async def aclose(self) -> None:
        if self._cache:
            self._cache.save()
        if self._owns_client:
            await self.client.aclose()

    async def check_urls(self, urls: list[str], source: Path | None = None) -> list[LinkResult]:
        return await asyncio.gather(*(self.check_url(url, source=source) for url in urls))

    async def check_url(self, url: str, source: Path | None = None) -> LinkResult:
        if self._is_excluded(url):
            return LinkResult(
                url=url,
                status=LinkStatus.SKIPPED,
                source=_source(source),
                message="excluded",
            )
        parsed = urlparse(url)
        if parsed.scheme in {"mailto", "tel", "javascript", "data"}:
            return LinkResult(
                url=url,
                status=LinkStatus.SKIPPED,
                source=_source(source),
                message="unsupported scheme",
            )
        if parsed.scheme in {"http", "https"}:
            return await self._check_remote(url, source)
        return self._check_local(url, source)

    async def _check_remote(self, url: str, source: Path | None) -> LinkResult:
        base_url, fragment = urldefrag(url)
        cached = self._cache.get(url) if self._cache else None
        if cached:
            return cached
        if self.options.respect_robots and not await self._robots.can_fetch(self.client, base_url):
            return LinkResult(
                url=url,
                status=LinkStatus.SKIPPED,
                source=_source(source),
                message="blocked by robots.txt",
            )
        async with self._semaphore:
            await self._pace()
            try:
                response = await self.client.get(base_url)
            except httpx.HTTPError as exc:
                result = LinkResult(
                    url=url,
                    status=LinkStatus.BROKEN,
                    source=_source(source),
                    message=str(exc),
                )
            else:
                if response.status_code >= 400:
                    result = LinkResult(
                        url=url,
                        status=LinkStatus.BROKEN,
                        source=_source(source),
                        status_code=response.status_code,
                    )
                elif fragment and not _html_has_anchor(response.text, fragment):
                    result = LinkResult(
                        url=url,
                        status=LinkStatus.BROKEN,
                        source=_source(source),
                        status_code=response.status_code,
                        message=f"missing anchor #{fragment}",
                    )
                else:
                    result = LinkResult(
                        url=url,
                        status=LinkStatus.OK,
                        source=_source(source),
                        status_code=response.status_code,
                    )
        if self._cache:
            self._cache.set(url, result)
        return result

    def _check_local(self, url: str, source: Path | None) -> LinkResult:
        raw_path, fragment = urldefrag(url)
        if not raw_path and fragment and source:
            target = source
        else:
            base = source.parent if source else self.options.root
            target = (base / raw_path).resolve()
        if not _is_within(target, self.options.root.resolve()):
            return LinkResult(
                url=url,
                status=LinkStatus.SKIPPED,
                source=_source(source),
                message="outside root",
            )
        if not target.exists():
            return LinkResult(
                url=url,
                status=LinkStatus.BROKEN,
                source=_source(source),
                message="file not found",
            )
        if fragment:
            try:
                document = extract_links_from_file(target)
            except UnicodeDecodeError:
                return LinkResult(
                    url=url,
                    status=LinkStatus.UNKNOWN,
                    source=_source(source),
                    message="cannot read anchors",
                )
            if fragment not in document.anchors:
                return LinkResult(
                    url=url,
                    status=LinkStatus.BROKEN,
                    source=_source(source),
                    message=f"missing anchor #{fragment}",
                )
        return LinkResult(url=url, status=LinkStatus.OK, source=_source(source))

    async def _pace(self) -> None:
        if self.options.rate_limit <= 0:
            return
        interval = 1 / self.options.rate_limit
        now = asyncio.get_running_loop().time()
        wait_for = self._last_request + interval - now
        if wait_for > 0:
            await asyncio.sleep(wait_for)
        self._last_request = asyncio.get_running_loop().time()

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
