import asyncio
from collections import Counter
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

    results = await checker.check_urls(
        ["https://example.com/docs#top", "https://example.com/missing"]
    )

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
async def test_checks_same_document_anchor_from_relative_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Overview\n\n[Back](#overview)", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    checker = LinkChecker(CheckOptions(root=tmp_path))

    results = await checker.check_urls(["#overview"], source=Path("README.md"))

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


@pytest.mark.asyncio
async def test_deduplicates_remote_requests_but_preserves_occurrences_and_fragments() -> None:
    requests: Counter[str] = Counter()

    async def handler(request: httpx.Request) -> httpx.Response:
        requests[str(request.url)] += 1
        return httpx.Response(200, text="<h1 id='present'>Present</h1>")

    checker = LinkChecker(
        CheckOptions(respect_robots=False),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    source = Path("README.md")

    results = await checker.check_urls(
        [
            "https://example.com/page#present",
            "https://example.com/page#missing",
            "https://example.com/page#present",
        ],
        source=source,
        lines=[2, 4, 8],
    )

    assert requests == {"https://example.com/page": 1}
    assert [result.status for result in results] == [
        LinkStatus.OK,
        LinkStatus.BROKEN,
        LinkStatus.OK,
    ]
    assert [result.line for result in results] == [2, 4, 8]
    assert all(result.source == "README.md" for result in results)
    await checker.aclose()


@pytest.mark.asyncio
async def test_local_urls_ignore_queries_decode_paths_and_handle_directories(
    tmp_path: Path,
) -> None:
    source = tmp_path / "README.md"
    encoded = tmp_path / "hello world.md"
    directory = tmp_path / "guide"
    source.write_text("# Top", encoding="utf-8")
    encoded.write_text("# Setup", encoding="utf-8")
    directory.mkdir()
    checker = LinkChecker(CheckOptions(root=tmp_path))

    results = await checker.check_urls(
        [
            "hello%20world.md?download=1#setup",
            "?preview=1#top",
            "guide/",
            "guide/#missing",
        ],
        source=source,
    )

    assert [result.status for result in results] == [
        LinkStatus.OK,
        LinkStatus.OK,
        LinkStatus.OK,
        LinkStatus.UNKNOWN,
    ]
    assert results[-1].message == "cannot validate anchor on directory"
    await checker.aclose()


@pytest.mark.asyncio
async def test_deduplicates_local_results_but_keeps_occurrence_lines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import linkchecker_py.checker as checker_module

    source = tmp_path / "README.md"
    guide = tmp_path / "guide.md"
    source.write_text("[one](guide.md#top)\n[again](guide.md#top)", encoding="utf-8")
    guide.write_text("# Top", encoding="utf-8")
    calls = 0
    original = checker_module.extract_links_from_file

    def counted_extract(path: Path):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        return original(path)

    monkeypatch.setattr(checker_module, "extract_links_from_file", counted_extract)
    checker = LinkChecker(CheckOptions(root=tmp_path))

    results = await checker.check_urls(
        ["guide.md#top", "guide.md#top"],
        source=source,
        lines=[1, 2],
    )

    assert calls == 1
    assert [result.line for result in results] == [1, 2]
    assert all(result.status is LinkStatus.OK for result in results)
    await checker.aclose()


@pytest.mark.asyncio
async def test_retries_transient_status_and_transport_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts: Counter[str] = Counter()
    delays: list[float] = []

    async def no_wait(delay: float) -> None:
        delays.append(delay)

    async def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        attempts[url] += 1
        if url.endswith("/status") and attempts[url] == 1:
            return httpx.Response(503, headers={"Retry-After": "0"})
        if url.endswith("/reset") and attempts[url] == 1:
            raise httpx.ConnectError("reset", request=request)
        return httpx.Response(200)

    monkeypatch.setattr(asyncio, "sleep", no_wait)
    checker = LinkChecker(
        CheckOptions(respect_robots=False, retries=1, retry_backoff=0.125),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    results = await checker.check_urls(["https://example.com/status", "https://example.com/reset"])

    assert all(result.status is LinkStatus.OK for result in results)
    assert attempts == {
        "https://example.com/status": 2,
        "https://example.com/reset": 2,
    }
    assert sorted(delays) == [0.0, 0.125]
    await checker.aclose()


@pytest.mark.asyncio
async def test_retries_are_bounded_when_transient_failure_persists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    async def no_wait(_delay: float) -> None:
        return None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(502)

    monkeypatch.setattr(asyncio, "sleep", no_wait)
    checker = LinkChecker(
        CheckOptions(respect_robots=False, retries=2),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    result = await checker.check_url("https://example.com/unavailable")

    assert result.status is LinkStatus.BROKEN
    assert result.status_code == 502
    assert attempts == 3
    await checker.aclose()


@pytest.mark.asyncio
async def test_rate_limit_serializes_each_host_without_blocking_other_hosts() -> None:
    starts: dict[str, float] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        starts[str(request.url)] = asyncio.get_running_loop().time()
        return httpx.Response(200)

    checker = LinkChecker(
        CheckOptions(respect_robots=False, rate_limit=20, concurrency=3),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    await checker.check_urls(
        [
            "https://one.test/a",
            "https://one.test/b",
            "https://two.test/a",
        ]
    )

    assert starts["https://one.test/b"] - starts["https://one.test/a"] >= 0.04
    assert abs(starts["https://two.test/a"] - starts["https://one.test/a"]) < 0.04
    await checker.aclose()


@pytest.mark.asyncio
async def test_concurrent_checks_coalesce_robots_fetch_and_pace_it() -> None:
    requests: list[tuple[str, float]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append((str(request.url), asyncio.get_running_loop().time()))
        return httpx.Response(404 if request.url.path == "/robots.txt" else 200)

    checker = LinkChecker(
        CheckOptions(rate_limit=20, concurrency=3),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    await checker.check_urls(["https://example.com/a", "https://example.com/b"])

    urls = [url for url, _time in requests]
    assert urls.count("https://example.com/robots.txt") == 1
    assert len(requests) == 3
    assert all(
        later[1] - earlier[1] >= 0.04
        for earlier, later in zip(requests, requests[1:], strict=False)
    )
    await checker.aclose()
