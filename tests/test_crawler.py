from collections import Counter

import httpx
import pytest

from linkchecker_py.checker import CheckOptions, LinkChecker
from linkchecker_py.crawler import crawl


@pytest.mark.asyncio
async def test_crawls_same_origin_until_depth_limit_and_checks_links_on_pages() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        pages = {
            "https://example.com/": "<a href='/one'>One</a><a href='https://external.test/x'>X</a>",
            "https://example.com/one": "<a href='/two'>Two</a><a href='/missing'>Missing</a>",
            "https://example.com/two": "<a href='/three'>Three</a>",
        }
        if str(request.url) in pages:
            return httpx.Response(200, text=pages[str(request.url)])
        return httpx.Response(404)

    checker = LinkChecker(
        CheckOptions(),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    seen = await crawl("https://example.com/", checker=checker, max_depth=1)

    assert seen == {
        "https://example.com/",
        "https://example.com/one",
        "https://example.com/two",
        "https://example.com/missing",
        "https://external.test/x",
    }
    await checker.aclose()


@pytest.mark.asyncio
async def test_crawl_reuses_page_responses_and_preserves_fragment_checks() -> None:
    requests: Counter[str] = Counter()

    async def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        requests[url] += 1
        pages = {
            "https://example.com/": (
                "<a href='/guide#present'>Good</a><a href='/guide#missing'>Bad anchor</a>"
            ),
            "https://example.com/guide": "<h2 id='present'>Present</h2>",
        }
        return httpx.Response(200, text=pages[url]) if url in pages else httpx.Response(404)

    checker = LinkChecker(
        CheckOptions(respect_robots=False),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    urls = sorted(await crawl("https://example.com/", checker, max_depth=1))
    results = await checker.check_urls(urls)

    assert "https://example.com/guide#present" in urls
    assert "https://example.com/guide#missing" in urls
    by_url = {result.url: result for result in results}
    assert by_url["https://example.com/guide#present"].status.value == "ok"
    assert by_url["https://example.com/guide#missing"].status.value == "broken"
    assert requests == {"https://example.com/": 1, "https://example.com/guide": 1}
    await checker.aclose()


@pytest.mark.asyncio
async def test_resolves_crawled_links_against_final_redirect_url() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.com/old":
            return httpx.Response(302, headers={"Location": "/new/base/"})
        if str(request.url) == "https://example.com/new/base/":
            return httpx.Response(200, text="<a href='child#top'>Child</a>")
        if str(request.url) == "https://example.com/new/base/child":
            return httpx.Response(200, text="<h1 id='top'>Top</h1>")
        return httpx.Response(404)

    checker = LinkChecker(
        CheckOptions(respect_robots=False),
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
        ),
    )

    urls = await crawl("https://example.com/old", checker, max_depth=1)

    assert "https://example.com/new/base/child#top" in urls
    await checker.aclose()
