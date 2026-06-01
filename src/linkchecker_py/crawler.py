from __future__ import annotations

from collections import deque
from urllib.parse import urldefrag, urlparse

import httpx

from linkchecker_py.checker import LinkChecker, extract_remote_links
from linkchecker_py.models import LinkStatus


async def crawl(start_url: str, checker: LinkChecker, max_depth: int = 1) -> set[str]:
    start = _canonical(start_url)
    origin = _origin(start)
    seen: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(start, 0)])

    while queue:
        url, depth = queue.popleft()
        if url in seen or depth > max_depth:
            continue
        seen.add(url)
        result = await checker.check_url(url)
        if result.status is not LinkStatus.OK or depth == max_depth:
            continue
        try:
            response = await checker.client.get(url)
        except httpx.HTTPError:
            continue
        for href in extract_remote_links(response.text, url):
            candidate = _canonical(href)
            if _origin(candidate) == origin and candidate not in seen:
                queue.append((candidate, depth + 1))
    return seen


def _canonical(url: str) -> str:
    return urldefrag(url)[0]


def _origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"
