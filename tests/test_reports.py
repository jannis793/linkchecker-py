import json

from linkchecker_py.models import LinkResult, LinkStatus
from linkchecker_py.reports import render_json_report, render_markdown_report, render_sarif_report


def test_renders_json_report() -> None:
    report = render_json_report(
        [LinkResult(url="https://example.com", status=LinkStatus.OK, status_code=200)]
    )

    assert '"url": "https://example.com"' in report
    assert '"status": "ok"' in report


def test_renders_markdown_report_summary_and_rows() -> None:
    report = render_markdown_report(
        [LinkResult(url="https://example.com/missing", status=LinkStatus.BROKEN, status_code=404)]
    )

    assert "# Link Check Report" in report
    assert "- Unknown: 0" in report
    assert "| https://example.com/missing | broken | 404 |" in report


def test_markdown_report_escapes_table_cells() -> None:
    report = render_markdown_report(
        [
            LinkResult(
                url="https://example.com/a|b",
                status=LinkStatus.BROKEN,
                message="bad | link\nretry later",
            )
        ]
    )

    assert "https://example.com/a\\|b" in report
    assert "bad \\| link<br>retry later" in report


def test_reports_include_source_lines_and_sarif_locations() -> None:
    result = LinkResult(
        url="missing.md",
        status=LinkStatus.BROKEN,
        source="docs/README.md",
        line=17,
        message="file not found",
    )

    json_report = json.loads(render_json_report([result]))
    markdown = render_markdown_report([result])
    sarif = json.loads(render_sarif_report([result]))

    assert json_report["links"][0]["line"] == 17
    assert "| docs/README.md | 17 |" in markdown
    location = sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"] == "docs/README.md"
    assert location["region"]["startLine"] == 17
