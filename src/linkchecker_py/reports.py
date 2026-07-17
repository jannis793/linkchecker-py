from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

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
        f"- Unknown: {summary['unknown']}",
        "",
        "| URL | Status | Code | Source | Line | Message |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        lines.append(
            f"| {_markdown_table_cell(result.url)} | {result.status.value} | "
            f"{result.status_code or ''} | {_markdown_table_cell(result.source or '')} | "
            f"{result.line or ''} | "
            f"{_markdown_table_cell(result.message or '')} |"
        )
    return "\n".join(lines) + "\n"


def render_sarif_report(results: list[LinkResult]) -> str:
    sarif_results = []
    for result in results:
        if result.status is not LinkStatus.BROKEN:
            continue
        entry: dict[str, object] = {
            "ruleId": "broken-link",
            "level": "error",
            "message": {"text": _result_message(result)},
        }
        if result.source:
            location: dict[str, object] = {
                "physicalLocation": {
                    "artifactLocation": {"uri": Path(result.source).as_posix()},
                }
            }
            if result.line:
                location["physicalLocation"]["region"] = {"startLine": result.line}  # type: ignore[index]
            entry["locations"] = [location]
        sarif_results.append(entry)
    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "linkchecker-py",
                        "informationUri": "https://github.com/jannis793/linkchecker-py",
                        "rules": [
                            {
                                "id": "broken-link",
                                "shortDescription": {"text": "Broken link"},
                            }
                        ],
                    }
                },
                "results": sarif_results,
            }
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _result_message(result: LinkResult) -> str:
    detail = result.message or (
        f"HTTP {result.status_code}" if result.status_code is not None else "link check failed"
    )
    return f"{result.url}: {detail}"


def summarize(results: list[LinkResult]) -> dict[str, int]:
    return {
        "total": len(results),
        "ok": sum(result.status is LinkStatus.OK for result in results),
        "broken": sum(result.status is LinkStatus.BROKEN for result in results),
        "skipped": sum(result.status is LinkStatus.SKIPPED for result in results),
        "unknown": sum(result.status is LinkStatus.UNKNOWN for result in results),
    }


def _markdown_table_cell(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")
