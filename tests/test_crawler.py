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
