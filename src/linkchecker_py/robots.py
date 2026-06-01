from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx


class RobotsCache:
    def __init__(self, user_agent: str) -> None:
        self.user_agent = user_agent
        self._parsers: dict[str, RobotFileParser | None] = {}

    async def can_fetch(self, client: httpx.AsyncClient, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return True
        origin = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._parsers.get(origin)
        if origin not in self._parsers:
            parser = await self._fetch_parser(client, origin)
            self._parsers[origin] = parser
        return True if parser is None else parser.can_fetch(self.user_agent, url)

    async def _fetch_parser(self, client: httpx.AsyncClient, origin: str) -> RobotFileParser | None:
        robots_url = f"{origin}/robots.txt"
        try:
            response = await client.get(robots_url)
        except httpx.HTTPError:
            return None
        if response.status_code >= 400:
            return None
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        return parser
