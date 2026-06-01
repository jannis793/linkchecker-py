from __future__ import annotations

import json
from dataclasses import asdict

from linkchecker_py.models import LinkResult, LinkStatus


def render_json_report(results: list[LinkResult]) -> str:
    rows = []
    for result in results:
        data = asdict(result)
        data["status"] = result.status.value
        rows.append(data)
    return json.dumps({"summary": summarize(results), "links": rows}, indent=2, sort_keys=True)


def render_markdown_report(results: list[LinkResult]) -> str:
    summary = summarize(results)
    lines = [
        "# Link Check Report",
        "",
        f"- Total: {summary['total']}",
        f"- OK: {summary['ok']}",
        f"- Broken: {summary['broken']}",
        f"- Skipped: {summary['skipped']}",
        "",
        "| URL | Status | Code | Source | Message |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in results:
        lines.append(
            f"| {result.url} | {result.status.value} | {result.status_code or ''} | "
            f"{result.source or ''} | {result.message or ''} |"
        )
    return "\n".join(lines) + "\n"


def summarize(results: list[LinkResult]) -> dict[str, int]:
    return {
        "total": len(results),
        "ok": sum(result.status is LinkStatus.OK for result in results),
        "broken": sum(result.status is LinkStatus.BROKEN for result in results),
        "skipped": sum(result.status is LinkStatus.SKIPPED for result in results),
        "unknown": sum(result.status is LinkStatus.UNKNOWN for result in results),
    }
