from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class LinkStatus(str, Enum):
    OK = "ok"
    BROKEN = "broken"
    SKIPPED = "skipped"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Link:
    url: str
    source: Path | None = None
    line: int | None = None


@dataclass(frozen=True)
class DocumentLinks:
    path: Path
    links: tuple[Link, ...]
    anchors: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class LinkResult:
    url: str
    status: LinkStatus
    source: str | None = None
    status_code: int | None = None
    message: str | None = None
    cached: bool = False
