from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from linkchecker_py.checker import CheckOptions, LinkChecker
from linkchecker_py.crawler import crawl
from linkchecker_py.extractors import extract_links_from_file, iter_supported_files
from linkchecker_py.models import LinkResult, LinkStatus
from linkchecker_py.reports import render_json_report, render_markdown_report, summarize

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
        typer.Option("--report", "-r", help="Write a JSON or Markdown report."),
    ] = None,
    concurrency: Annotated[int, typer.Option("--concurrency", "-c", min=1)] = 20,
    rate_limit: Annotated[
        float,
        typer.Option("--rate-limit", help="Remote requests per second. 0 disables pacing."),
    ] = 0.0,
    cache: Annotated[
        bool,
        typer.Option("--cache", help="Cache remote results between runs."),
    ] = False,
    no_robots: Annotated[
        bool,
        typer.Option("--no-robots", help="Do not consult robots.txt."),
    ] = False,
) -> None:
    """Check links found in Markdown and HTML files."""

    raise_code = asyncio.run(
        _run_files(paths, exclude or [], report, concurrency, rate_limit, cache, not no_robots)
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
        typer.Option("--report", "-r", help="Write a JSON or Markdown report."),
    ] = None,
    concurrency: Annotated[int, typer.Option("--concurrency", "-c", min=1)] = 20,
    rate_limit: Annotated[
        float,
        typer.Option("--rate-limit", help="Remote requests per second. 0 disables pacing."),
    ] = 0.0,
    cache: Annotated[
        bool,
        typer.Option("--cache", help="Cache remote results between runs."),
    ] = False,
    no_robots: Annotated[
        bool,
        typer.Option("--no-robots", help="Do not consult robots.txt."),
    ] = False,
) -> None:
    """Crawl a website and check discovered links."""

    raise_code = asyncio.run(
        _run_site(url, depth, exclude or [], report, concurrency, rate_limit, cache, not no_robots)
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
) -> int:
    files_to_scan = iter_supported_files(paths)
    if not files_to_scan:
        error_console.print(
            "[red]No supported Markdown or HTML files found.[/red] "
            "Pass .md, .markdown, .html, or .htm files or directories."
        )
        return 2
    options = CheckOptions(
        root=_scan_root(paths),
        exclude=exclude,
        concurrency=concurrency,
        rate_limit=rate_limit,
        cache=cache,
        respect_robots=respect_robots,
    )
    checker = LinkChecker(options)
    try:
        results: list[LinkResult] = []
        for path in files_to_scan:
            document = extract_links_from_file(path)
            urls = [link.url for link in document.links]
            results.extend(await checker.check_urls(urls, source=path))
    finally:
        await checker.aclose()
    _render(results)
    _write_report(report, results)
    return 1 if any(result.status is LinkStatus.BROKEN for result in results) else 0


async def _run_site(
    url: str,
    depth: int,
    exclude: list[str],
    report: Path | None,
    concurrency: int,
    rate_limit: float,
    cache: bool,
    respect_robots: bool,
) -> int:
    checker = LinkChecker(
        CheckOptions(
            exclude=exclude,
            concurrency=concurrency,
            rate_limit=rate_limit,
            cache=cache,
            respect_robots=respect_robots,
        )
    )
    try:
        urls = sorted(await crawl(url, checker=checker, max_depth=depth))
        results = await checker.check_urls(urls)
    finally:
        await checker.aclose()
    _render(results)
    _write_report(report, results)
    return 1 if any(result.status is LinkStatus.BROKEN for result in results) else 0


def _render(results: list[LinkResult]) -> None:
    totals = summarize(results)
    table = Table(title=f"Link check: {totals['broken']} broken of {totals['total']}")
    table.add_column("Status")
    table.add_column("URL", overflow="fold")
    table.add_column("Code")
    table.add_column("Source", overflow="fold")
    table.add_column("Message", overflow="fold")
    for result in results:
        style = _status_style(result.status)
        table.add_row(
            f"[{style}]{result.status.value}[/{style}]",
            result.url,
            str(result.status_code or ""),
            result.source or "",
            result.message or "",
        )
    console.print(table)


def _write_report(path: Path | None, results: list[LinkResult]) -> None:
    if not path:
        return
    if path.suffix.lower() in {".md", ".markdown"}:
        path.write_text(render_markdown_report(results), encoding="utf-8")
    else:
        path.write_text(render_json_report(results), encoding="utf-8")


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
