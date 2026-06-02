from linkchecker_py.models import LinkResult, LinkStatus
from linkchecker_py.reports import render_json_report, render_markdown_report


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
