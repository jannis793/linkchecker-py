from pathlib import Path

import pytest
from typer.testing import CliRunner

import linkchecker_py
from linkchecker_py.cli import _exit_code, _run_files, _settings, app
from linkchecker_py.models import LinkResult, LinkStatus
from linkchecker_py.reports import render_json_report


def test_package_version_matches_project_metadata() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert 'dynamic = ["version"]' in pyproject
    assert 'version = { attr = "linkchecker_py._version.__version__" }' in pyproject
    assert linkchecker_py.__version__ == "0.1.3"


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


def test_project_config_is_discovered_and_cli_values_override_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.linkchecker-py]
exclude = ["configured/*"]
concurrency = 3
rate_limit = 2.5
cache = true
report = "artifacts/links.sarif"
respect_robots = false
retries = 4
fail_on = "unknown"
github_annotations = true
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    configured = _settings(None)
    overridden = _settings(None, concurrency=9, cache=False, exclude=["cli/*"])

    assert configured.concurrency == 3
    assert configured.report == tmp_path / "artifacts/links.sarif"
    assert configured.respect_robots is False
    assert configured.fail_on == "unknown"
    assert overridden.concurrency == 9
    assert overridden.cache is False
    assert overridden.exclude == ["cli/*"]
    assert overridden.rate_limit == 2.5


def test_fail_on_unknown_changes_exit_behavior() -> None:
    results = [LinkResult(url="directory/#anchor", status=LinkStatus.UNKNOWN)]

    assert _exit_code(results, "broken") == 0
    assert _exit_code(results, "unknown") == 1


def test_cli_emits_annotations_and_writes_sarif(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    report = tmp_path / "report.sarif"
    readme.write_text("# Links\n\n[missing](missing.md)\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "files",
            str(readme),
            "--github-annotations",
            "--report",
            str(report),
            "--no-robots",
        ],
    )

    assert result.exit_code == 1
    assert f"::error file={readme},line=3::missing.md: file not found" in result.output
    assert '"version": "2.1.0"' in report.read_text(encoding="utf-8")


def test_cli_rejects_invalid_fail_on(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Fine", encoding="utf-8")

    result = CliRunner().invoke(app, ["files", str(readme), "--fail-on", "everything"])

    assert result.exit_code == 2
    assert "must be 'broken' or 'unknown'" in result.output
