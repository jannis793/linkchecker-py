from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from linkchecker_py.checker import CheckOptions, LinkChecker
from linkchecker_py.config import ProjectConfig, load_config
from linkchecker_py.crawler import crawl
from linkchecker_py.extractors import extract_links_from_file, iter_supported_files
from linkchecker_py.models import LinkResult, LinkStatus
from linkchecker_py.reports import (
    render_json_report,
    render_markdown_report,
    render_sarif_report,
    summarize,
)

app = typer.Typer(
    no_args_is_help=True,
    help="Fast async broken-link checker for files and websites.",
)
console = Console()
error_console = Console(stderr=True)


@app.command()
def files(
    paths: Annotated[
        list[Path],
        typer.Argument(help="Markdown/HTML files or directories to scan."),
    ],
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", "-x", help="Glob pattern to skip."),
    ] = None,
    report: Annotated[
        Path | None,
        typer.Option("--report", "-r", help="Write a JSON, Markdown, or SARIF report."),
    ] = None,
    concurrency: Annotated[int | None, typer.Option("--concurrency", "-c", min=1)] = None,
    rate_limit: Annotated[
        float | None,
        typer.Option("--rate-limit", min=0, help="Per-host requests/second; 0 disables pacing."),
    ] = None,
    cache: Annotated[
        bool | None,
        typer.Option("--cache/--no-cache", help="Cache remote results between runs."),
    ] = None,
    robots: Annotated[
        bool | None,
        typer.Option("--robots/--no-robots", help="Consult robots.txt."),
    ] = None,
    retries: Annotated[
        int | None,
        typer.Option("--retries", min=0, help="Retries after transient request failures."),
    ] = None,
    retry_backoff: Annotated[
        float | None,
        typer.Option("--retry-backoff", min=0, help="Initial retry delay in seconds."),
    ] = None,
    fail_on: Annotated[
        str | None,
        typer.Option("--fail-on", help="Failure threshold: broken or unknown."),
    ] = None,
    github_annotations: Annotated[
        bool | None,
        typer.Option(
            "--github-annotations/--no-github-annotations",
            help="Emit GitHub Actions workflow annotations.",
        ),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Project config file (otherwise auto-discovered)."),
    ] = None,
) -> None:
    """Check links found in Markdown and HTML files."""
    settings = _settings(
        config,
        exclude=exclude,
        report=report,
        concurrency=concurrency,
        rate_limit=rate_limit,
        cache=cache,
        respect_robots=robots,
        retries=retries,
        retry_backoff=retry_backoff,
        fail_on=fail_on,
        github_annotations=github_annotations,
    )
    raise_code = asyncio.run(
        _run_files(
            paths,
            settings.exclude,
            settings.report,
            settings.concurrency,
            settings.rate_limit,
            settings.cache,
            settings.respect_robots,
            settings.retries,
            settings.retry_backoff,
            settings.fail_on,
            settings.github_annotations,
        )
    )
    raise typer.Exit(raise_code)


@app.command()
def site(
    url: Annotated[str, typer.Argument(help="Website URL to crawl.")],
    depth: Annotated[
        int,
        typer.Option("--depth", "-d", min=0, help="Maximum same-origin crawl depth."),
    ] = 1,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", "-x", help="Glob pattern to skip."),
    ] = None,
    report: Annotated[
        Path | None,
        typer.Option("--report", "-r", help="Write a JSON, Markdown, or SARIF report."),
    ] = None,
    concurrency: Annotated[int | None, typer.Option("--concurrency", "-c", min=1)] = None,
    rate_limit: Annotated[
        float | None,
        typer.Option("--rate-limit", min=0, help="Per-host requests/second; 0 disables pacing."),
    ] = None,
    cache: Annotated[
        bool | None,
        typer.Option("--cache/--no-cache", help="Cache remote results between runs."),
    ] = None,
    robots: Annotated[
        bool | None,
        typer.Option("--robots/--no-robots", help="Consult robots.txt."),
    ] = None,
    retries: Annotated[int | None, typer.Option("--retries", min=0)] = None,
    retry_backoff: Annotated[float | None, typer.Option("--retry-backoff", min=0)] = None,
    fail_on: Annotated[
        str | None,
        typer.Option("--fail-on", help="Failure threshold: broken or unknown."),
    ] = None,
    github_annotations: Annotated[
        bool | None,
        typer.Option("--github-annotations/--no-github-annotations"),
    ] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """Crawl a website and check discovered links."""
    settings = _settings(
        config,
        exclude=exclude,
        report=report,
        concurrency=concurrency,
        rate_limit=rate_limit,
        cache=cache,
        respect_robots=robots,
        retries=retries,
        retry_backoff=retry_backoff,
        fail_on=fail_on,
        github_annotations=github_annotations,
    )
    raise_code = asyncio.run(
        _run_site(
            url,
            depth,
            settings.exclude,
            settings.report,
            settings.concurrency,
            settings.rate_limit,
            settings.cache,
            settings.respect_robots,
            settings.retries,
            settings.retry_backoff,
            settings.fail_on,
            settings.github_annotations,
        )
    )
    raise typer.Exit(raise_code)


async def _run_files(
    paths: list[Path],
    exclude: list[str],
    report: Path | None,
    concurrency: int,
    rate_limit: float,
    cache: bool,
    respect_robots: bool,
    retries: int = 2,
    retry_backoff: float = 0.25,
    fail_on: str = "broken",
    github_annotations: bool = False,
) -> int:
    files_to_scan = iter_supported_files(paths)
    if not files_to_scan:
        error_console.print(
            "[red]No supported Markdown or HTML files found.[/red] "
            "Pass .md, .markdown, .html, or .htm files or directories."
        )
        return 2
    checker = LinkChecker(
        CheckOptions(
            root=_scan_root(paths),
            exclude=exclude,
            concurrency=concurrency,
            rate_limit=rate_limit,
            cache=cache,
            respect_robots=respect_robots,
            retries=retries,
            retry_backoff=retry_backoff,
        )
    )
    try:
        results: list[LinkResult] = []
        for path in files_to_scan:
            document = extract_links_from_file(path)
            results.extend(await checker.check_links(document.links))
    finally:
        await checker.aclose()
    _present(results, report, github_annotations)
    return _exit_code(results, fail_on)


async def _run_site(
    url: str,
    depth: int,
    exclude: list[str],
    report: Path | None,
    concurrency: int,
    rate_limit: float,
    cache: bool,
    respect_robots: bool,
    retries: int = 2,
    retry_backoff: float = 0.25,
    fail_on: str = "broken",
    github_annotations: bool = False,
) -> int:
    checker = LinkChecker(
        CheckOptions(
            exclude=exclude,
            concurrency=concurrency,
            rate_limit=rate_limit,
            cache=cache,
            respect_robots=respect_robots,
            retries=retries,
            retry_backoff=retry_backoff,
        )
    )
    try:
        urls = sorted(await crawl(url, checker=checker, max_depth=depth))
        results = await checker.check_urls(urls)
    finally:
        await checker.aclose()
    _present(results, report, github_annotations)
    return _exit_code(results, fail_on)


def _present(results: list[LinkResult], report: Path | None, annotations: bool) -> None:
    _render(results)
    _write_report(report, results)
    if annotations:
        _render_github_annotations(results)


def _render(results: list[LinkResult]) -> None:
    totals = summarize(results)
    table = Table(title=f"Link check: {totals['broken']} broken of {totals['total']}")
    table.add_column("Status")
    table.add_column("URL", overflow="fold")
    table.add_column("Code")
    table.add_column("Source", overflow="fold")
    table.add_column("Line")
    table.add_column("Message", overflow="fold")
    for result in results:
        style = _status_style(result.status)
        table.add_row(
            f"[{style}]{result.status.value}[/{style}]",
            result.url,
            str(result.status_code or ""),
            result.source or "",
            str(result.line or ""),
            result.message or "",
        )
    console.print(table)


def _render_github_annotations(results: list[LinkResult]) -> None:
    for result in results:
        if result.status not in {LinkStatus.BROKEN, LinkStatus.UNKNOWN}:
            continue
        level = "error" if result.status is LinkStatus.BROKEN else "warning"
        properties = []
        if result.source:
            properties.append(f"file={_escape_property(result.source)}")
        if result.line:
            properties.append(f"line={result.line}")
        suffix = f" {','.join(properties)}" if properties else ""
        detail = result.message or (
            f"HTTP {result.status_code}" if result.status_code is not None else result.status.value
        )
        console.print(
            f"::{level}{suffix}::{_escape_message(f'{result.url}: {detail}')}",
            markup=False,
            highlight=False,
            soft_wrap=True,
        )


def _write_report(path: Path | None, results: list[LinkResult]) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    lower_name = path.name.lower()
    if path.suffix.lower() in {".md", ".markdown"}:
        rendered = render_markdown_report(results)
    elif lower_name.endswith((".sarif", ".sarif.json")):
        rendered = render_sarif_report(results)
    else:
        rendered = render_json_report(results)
    path.write_text(rendered, encoding="utf-8")


def _settings(config_path: Path | None, **overrides: object) -> ProjectConfig:
    try:
        settings = load_config(config_path)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc), param_hint="--config") from exc
    values = {name: value for name, value in overrides.items() if value is not None}
    if "fail_on" in values and values["fail_on"] not in {"broken", "unknown"}:
        raise typer.BadParameter("must be 'broken' or 'unknown'", param_hint="--fail-on")
    return replace(settings, **values)


def _exit_code(results: list[LinkResult], fail_on: str) -> int:
    failing = {LinkStatus.BROKEN}
    if fail_on == "unknown":
        failing.add(LinkStatus.UNKNOWN)
    return 1 if any(result.status in failing for result in results) else 0


def _scan_root(paths: list[Path]) -> Path:
    candidates = [path.resolve() if path.is_dir() else path.resolve().parent for path in paths]
    if not candidates:
        return Path.cwd().resolve()
    return Path(os.path.commonpath(candidates))


def _status_style(status: LinkStatus) -> str:
    if status is LinkStatus.OK:
        return "green"
    if status is LinkStatus.BROKEN:
        return "red"
    return "yellow"


def _escape_message(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(value: str) -> str:
    return _escape_message(value).replace(":", "%3A").replace(",", "%2C")
