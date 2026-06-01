from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from platformdirs import user_cache_dir

from linkchecker_py.models import LinkResult, LinkStatus


class ResultCache:
    def __init__(self, path: Path | None = None, ttl_seconds: int = 3600) -> None:
        self.path = path or Path(user_cache_dir("linkchecker-py")) / "results.json"
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, dict[str, object]] = {}
        self._load()

    def get(self, key: str) -> LinkResult | None:
        entry = self._entries.get(key)
        if not entry:
            return None
        if time.time() - float(entry.get("created_at", 0)) > self.ttl_seconds:
            return None
        result = dict(entry["result"])  # type: ignore[index]
        result["status"] = LinkStatus(result["status"])
        result.pop("cached", None)
        return LinkResult(**result, cached=True)

    def set(self, key: str, result: LinkResult) -> None:
        data = asdict(result)
        data["status"] = result.status.value
        data["cached"] = False
        self._entries[key] = {"created_at": time.time(), "result": data}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._entries, indent=2, sort_keys=True), encoding="utf-8")

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            self._entries = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._entries = {}
