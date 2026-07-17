from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx


class RobotsCache:
    """Run-local, concurrency-safe robots.txt parser cache."""

    def __init__(self, user_agent: str) -> None:
        self.user_agent = user_agent
        self._parsers: dict[str, RobotFileParser | None] = {}
        self._tasks: dict[str, asyncio.Task[RobotFileParser | None]] = {}
        self._lock = asyncio.Lock()

    async def can_fetch(
        self,
        client: Callable[[str], Awaitable[httpx.Response]] | httpx.AsyncClient,
        url: str,
    ) -> bool:
        fetch_call = client.get if isinstance(client, httpx.AsyncClient) else client
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return True
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin in self._parsers:
            parser = self._parsers[origin]
        else:
            async with self._lock:
                task = self._tasks.get(origin)
                if task is None:
                    task = asyncio.create_task(self._fetch_parser(fetch_call, origin))
                    self._tasks[origin] = task
            parser = await task
            async with self._lock:
                self._parsers[origin] = parser
                self._tasks.pop(origin, None)
        return True if parser is None else parser.can_fetch(self.user_agent, url)

    async def _fetch_parser(
        self,
        fetch: Callable[[str], Awaitable[httpx.Response]],
        origin: str,
    ) -> RobotFileParser | None:
        robots_url = f"{origin}/robots.txt"
        try:
            response = await fetch(robots_url)
        except httpx.HTTPError:
            return None
        if response.status_code >= 400:
            return None
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        return parser
