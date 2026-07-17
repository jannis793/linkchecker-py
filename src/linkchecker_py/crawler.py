from __future__ import annotations

from collections import deque
from urllib.parse import urldefrag, urlparse

from linkchecker_py.checker import LinkChecker, extract_remote_links
from linkchecker_py.models import LinkStatus


async def crawl(start_url: str, checker: LinkChecker, max_depth: int = 1) -> set[str]:
    start_page = _page_url(start_url)
    origin = _origin(start_page)
    seen_pages: set[str] = set()
    found_urls: set[str] = {start_url}
    queue: deque[tuple[str, int]] = deque([(start_page, 0)])

    while queue:
        url, depth = queue.popleft()
        if url in seen_pages or depth > max_depth:
            continue
        seen_pages.add(url)
        result = await checker.check_url(url)
        if result.status is not LinkStatus.OK:
            continue
        response = await checker.get_response(url)
        if response is None:
            continue
        for candidate in extract_remote_links(response.text, str(response.url)):
            found_urls.add(candidate)
            page_url = _page_url(candidate)
            if _origin(page_url) == origin and depth < max_depth and page_url not in seen_pages:
                queue.append((page_url, depth + 1))
    return found_urls


def _page_url(url: str) -> str:
    return urldefrag(url)[0]


_canonical = _page_url


def _origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"
