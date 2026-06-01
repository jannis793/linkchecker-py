# linkchecker-py

[![CI](https://github.com/jannis793/linkchecker-py/actions/workflows/ci.yml/badge.svg)](https://github.com/jannis793/linkchecker-py/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/linkchecker-py.svg)](https://pypi.org/project/linkchecker-py/)
[![Python](https://img.shields.io/pypi/pyversions/linkchecker-py.svg)](https://pypi.org/project/linkchecker-py/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`linkchecker-py` is a modern async CLI for finding broken links in Markdown files, HTML files, and small to medium websites. It is built for documentation maintainers who want fast checks locally, clean CI output, and reports they can paste into pull requests.

![Terminal demo](docs/demo-terminal.svg)

## Highlights

- Check Markdown and HTML files with a `src` layout Python package.
- Crawl websites with a same-origin depth limit.
- Validate HTTP status codes and URL fragments such as `#install`.
- Check local file links and generated Markdown heading anchors.
- Exclude noisy links with glob patterns.
- Control concurrency and rate limiting for polite checks.
- Respect `robots.txt` by default.
- Cache remote results between runs.
- Print Rich terminal tables and write JSON or Markdown reports.

## Install

Use `pipx` for the CLI:

```bash
pipx install linkchecker-py
```

For local development:

```bash
git clone https://github.com/jannis793/linkchecker-py.git
cd linkchecker-py
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Usage

Check a documentation folder:

```bash
linkchecker-py files README.md docs/
```

Write a Markdown report:

```bash
linkchecker-py files README.md docs/ --report link-report.md
```

Write a JSON report for CI artifacts:

```bash
linkchecker-py files docs/ --report link-report.json
```

Crawl a website up to depth 2:

```bash
linkchecker-py site https://example.com --depth 2
```

Skip links that are rate-limited or intentionally private:

```bash
linkchecker-py files docs/ --exclude "https://localhost/*" --exclude "*/private/*"
```

Be extra polite to a remote site:

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

### Exit Codes

`linkchecker-py` is designed for CI:

- `0`: all checked links are OK, skipped, or unknown.
- `1`: at least one checked link is broken.
- `2`: the command could not run as requested, such as when `files` finds no supported Markdown or HTML files.

### Configuration

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

## Reports

JSON reports contain a summary and a row per checked link:

```json
{
  "summary": {
    "total": 2,
    "ok": 1,
    "broken": 1,
    "skipped": 0,
    "unknown": 0
  },
  "links": []
}
```

Markdown reports are designed for pull request comments and release notes.

## CI Recipes

```yaml
- name: Check documentation links
  run: |
    python -m pip install linkchecker-py
    linkchecker-py files README.md docs/ --report link-report.md
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

## Troubleshooting

- If a URL is reported as blocked by `robots.txt`, either keep the skip or re-run with `--no-robots` for sites you control.
- If a site rate-limits requests, lower `--concurrency` and set `--rate-limit`.
- If local file links are skipped as outside the root, run the command from the documentation root or pass all relevant files/directories together.
- If generated documentation uses custom heading IDs, prefer explicit HTML anchors or link to those IDs directly.

## Limitations

- Website crawling is intended for small to medium sites, not exhaustive internet-scale crawls.
- JavaScript-rendered links are not executed in a browser.
- Markdown heading anchors follow common GitHub-style slug behavior; documentation systems with custom slug rules can differ.
- Cache entries are local to the current user cache directory and expire after one hour by default.

## Roadmap

- PyPI release automation.
- SARIF output for GitHub code scanning.
- Per-host rate-limit configuration.
- Project-level configuration file.
- Persistent crawl manifests for very large documentation sites.

## Contributing

Bug reports, focused feature requests, and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and review expectations.

## Changelog

Release notes are tracked in [CHANGELOG.md](CHANGELOG.md).

## License

MIT. See [LICENSE](LICENSE).
