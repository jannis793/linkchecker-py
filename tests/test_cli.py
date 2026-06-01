from pathlib import Path

import pytest

from linkchecker_py.cli import _run_files
from linkchecker_py.reports import render_json_report


@pytest.mark.asyncio
async def test_file_command_uses_input_parent_as_root_for_absolute_paths(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    guide = tmp_path / "guide.md"
    report = tmp_path / "report.json"
    readme.write_text("[ok](guide.md#setup) [bad](missing.md)", encoding="utf-8")
    guide.write_text("# Setup", encoding="utf-8")

    exit_code = await _run_files([readme], [], report, 5, 0, False, False)

    assert exit_code == 1
    report_text = report.read_text(encoding="utf-8")
    assert '"url": "guide.md#setup"' in report_text
    assert '"url": "missing.md"' in report_text
    assert '"status": "ok"' in report_text
    assert '"status": "broken"' in report_text


def test_json_report_keeps_unknown_count_visible() -> None:
    report = render_json_report([])

    assert '"unknown": 0' in report


@pytest.mark.asyncio
async def test_file_command_returns_usage_error_when_no_supported_files(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    notes = tmp_path / "notes.txt"
    notes.write_text("https://example.com", encoding="utf-8")

    exit_code = await _run_files([notes], [], None, 5, 0, False, False)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "No supported Markdown or HTML files found" in captured.err
