# linkchecker-py

[![CI](https://github.com/jannis793/linkchecker-py/actions/workflows/ci.yml/badge.svg)](https://github.com/jannis793/linkchecker-py/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`linkchecker-py` is a fast async CLI for finding broken links in Markdown files, HTML files, and small to medium websites. It exists for documentation maintainers who want deterministic local checks, clean CI failures, and reports that can be attached to pull requests.

![Terminal demo](docs/demo-terminal.svg)

## Project Status

This project is early but actively maintained. The core CLI, parser, checker, crawler, reports, tests, and CI are in place, but the project should still be treated as pre-1.0 while configuration, release automation, and broader compatibility work mature.

The package metadata is prepared for publishing, but this README does not claim PyPI availability until the package is actually published.

## GitHub Metadata

Suggested repository description:

> Async Python CLI for finding broken links in Markdown, HTML, and small websites.

Recommended GitHub topics:

`link-checker`, `markdown`, `html`, `cli`, `python`, `documentation`, `ci`, `httpx`, `rich`

## Highlights

- Checks Markdown and HTML files from a `src` layout Python package.
- Crawls same-origin websites with a configurable depth limit.
- Validates HTTP status codes and URL fragments such as `#install`.
- Checks local file links and generated Markdown heading anchors.
- Excludes noisy links with glob patterns.
- Controls concurrency and rate limiting for polite checks.
- Respects `robots.txt` by default.
- Caches remote results between runs.
- Prints Rich terminal tables and writes JSON or Markdown reports.

## Install

### From source

```bash
git clone https://github.com/jannis793/linkchecker-py.git
cd linkchecker-py
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

### Development install

```bash
python -m pip install -e ".[dev]"
```

Once the package is published, the intended CLI install path will be:

```bash
pipx install linkchecker-py
```

## Quickstart

Check the README and docs in this repository:

```bash
linkchecker-py files README.md docs/
```

Write a Markdown report:

```bash
linkchecker-py files README.md docs/ --report link-report.md
```

Write a JSON report for CI artifacts:

```bash
linkchecker-py files README.md docs/ --report link-report.json
```

Crawl a website up to depth 2:

```bash
linkchecker-py site https://example.com --depth 2
```

## Common Options

Skip links that are rate-limited, private, or intentionally local:

```bash
linkchecker-py files docs/ --exclude "https://localhost/*" --exclude "*/private/*"
```

Lower concurrency and add request pacing for remote checks:

```bash
linkchecker-py site https://example.com --depth 1 --concurrency 4 --rate-limit 1
```

Use cached remote results:

```bash
linkchecker-py files docs/ --cache
```

Skip `robots.txt` checks for private staging sites you own:

```bash
linkchecker-py site https://staging.example.com --no-robots
```

There is no project-level config file yet. Keep options explicit in scripts or CI commands:

```bash
linkchecker-py files README.md docs/ \
  --exclude "https://localhost/*" \
  --exclude "*/private/*" \
  --concurrency 8 \
  --rate-limit 2 \
  --cache \
  --report link-report.md
```

## Output and Exit Codes

Terminal output is a Rich table with status, URL, status code, source, and message. JSON reports contain a summary plus a row per checked link:

```json
{
  "summary": {
    "broken": 1,
    "ok": 1,
    "skipped": 0,
    "total": 2,
    "unknown": 0
  },
  "links": []
}
```

Exit codes are designed for CI:

- `0`: all checked links are OK, skipped, or unknown.
- `1`: at least one checked link is broken.
- `2`: the command could not run as requested, such as when `files` finds no supported Markdown or HTML files.

## CI Usage

Source checkout workflow:

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
- run: python -m pip install -e .
- run: linkchecker-py files README.md docs/ --report link-report.md
```

Upload the report even when broken links fail the job:

```yaml
- name: Check documentation links
  run: linkchecker-py files README.md docs/ --report link-report.md
- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: link-report
    path: link-report.md
```

The repository's own CI runs `ruff check .` and `pytest` on Python 3.10, 3.11, 3.12, and 3.13.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
python -m build
```

Release steps are documented in [docs/RELEASE.md](docs/RELEASE.md). The current tag is `v0.1.1`; the next patch release would normally be `v0.1.2` if the changes are documentation or bug fixes.

## Troubleshooting

- If a URL is reported as blocked by `robots.txt`, keep the skip or re-run with `--no-robots` for sites you control.
- If a site rate-limits requests, lower `--concurrency` and set `--rate-limit`.
- If local file links are skipped as outside the root, run the command from the documentation root or pass all relevant files/directories together.
- If generated documentation uses custom heading IDs, prefer explicit HTML anchors or link to those IDs directly.

## Limitations

- Website crawling is intended for small to medium sites, not exhaustive internet-scale crawls.
- JavaScript-rendered links are not executed in a browser.
- Markdown heading anchors follow common GitHub-style slug behavior; documentation systems with custom slug rules can differ.
- Cache entries are local to the current user cache directory and expire after one hour by default.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for scoped near-term improvements and suggested starter issues.

## Contributing

Bug reports, focused feature requests, and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, testing, and review expectations. Please report security issues through [SECURITY.md](SECURITY.md).

## Changelog

Release notes are tracked in [CHANGELOG.md](CHANGELOG.md).

## License

MIT. See [LICENSE](LICENSE).
