from pathlib import Path

import httpx
import pytest

from linkchecker_py.cache import ResultCache
from linkchecker_py.checker import CheckOptions, LinkChecker
from linkchecker_py.models import LinkResult, LinkStatus
from linkchecker_py.robots import RobotsCache


@pytest.mark.asyncio
async def test_checks_remote_links_and_anchors_with_mock_transport() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.com/docs":
            return httpx.Response(200, text="<h1 id='top'>Top</h1>")
        return httpx.Response(404)

    checker = LinkChecker(
        CheckOptions(),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    results = await checker.check_urls(["https://example.com/docs#top", "https://example.com/missing"])

    assert results[0].status is LinkStatus.OK
    assert results[1].status is LinkStatus.BROKEN
    await checker.aclose()


@pytest.mark.asyncio
async def test_reports_missing_remote_anchor() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<h1 id='present'>Present</h1>")

    checker = LinkChecker(
        CheckOptions(),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    results = await checker.check_urls(["https://example.com/docs#absent"])

    assert results[0].status is LinkStatus.BROKEN
    assert "anchor" in (results[0].message or "")
    await checker.aclose()


@pytest.mark.asyncio
async def test_excludes_matching_patterns() -> None:
    checker = LinkChecker(CheckOptions(exclude=["*/skip/*"]))

    results = await checker.check_urls(["https://example.com/skip/this"])

    assert results[0].status is LinkStatus.SKIPPED
    await checker.aclose()


@pytest.mark.asyncio
async def test_checks_local_file_anchor(tmp_path: Path) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text("# Install\n\nReady.", encoding="utf-8")

    checker = LinkChecker(CheckOptions(root=tmp_path))

    results = await checker.check_urls(["guide.md#install"], source=tmp_path / "README.md")

    assert results[0].status is LinkStatus.OK
    await checker.aclose()


@pytest.mark.asyncio
async def test_decodes_percent_encoded_fragments_for_local_anchors(tmp_path: Path) -> None:
    guide = tmp_path / "guide.html"
    guide.write_text("<h1 id='hello world'>Hello</h1>", encoding="utf-8")

    checker = LinkChecker(CheckOptions(root=tmp_path))

    results = await checker.check_urls(["guide.html#hello%20world"], source=tmp_path / "README.md")

    assert results[0].status is LinkStatus.OK
    await checker.aclose()


@pytest.mark.asyncio
async def test_decodes_percent_encoded_fragments_for_remote_anchors() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<h1 id='hello world'>Hello</h1>")

    checker = LinkChecker(
        CheckOptions(respect_robots=False),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    results = await checker.check_urls(["https://example.com/docs#hello%20world"])

    assert results[0].status is LinkStatus.OK
    await checker.aclose()


def test_result_cache_round_trips_link_results(tmp_path: Path) -> None:
    cache_path = tmp_path / "results.json"
    cache = ResultCache(cache_path)
    cache.set(
        "https://example.com",
        LinkResult(url="https://example.com", status=LinkStatus.OK, status_code=200),
    )
    cache.save()

    cached = ResultCache(cache_path).get("https://example.com")

    assert cached == LinkResult(
        url="https://example.com",
        status=LinkStatus.OK,
        status_code=200,
        cached=True,
    )


@pytest.mark.asyncio
async def test_robots_cache_blocks_disallowed_urls() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.com/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
        return httpx.Response(200)

    robots = RobotsCache("linkchecker-py-test")
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    try:
        assert await robots.can_fetch(client, "https://example.com/public")
        assert not await robots.can_fetch(client, "https://example.com/private/page")
    finally:
        await client.aclose()
