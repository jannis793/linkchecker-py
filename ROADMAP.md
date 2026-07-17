# Roadmap

`linkchecker-py` is early and intentionally scoped. The near-term goal is to make local and CI link checks reliable for documentation repositories without pretending to be a full web crawler.

## Near term

- Add JUnit XML output for CI systems that already collect test reports.
- Add per-host rate-limit settings for mixed documentation and API-reference sites.
- Improve Markdown anchor compatibility for documentation systems with custom slug rules.
- Expand docs-site crawler examples for common static site generators.
- Add more report-focused tests around escaping, source paths, and unknown results.

## Later

- Add persistent crawl manifests for larger documentation sites.
- Add optional authentication/header configuration for private documentation.
- Add release automation once PyPI publishing is configured.

## Suggested starter issues

These are maintainer-generated ideas for contributors. They are not external feature requests.

- **JUnit report support**: add JUnit XML output for CI systems that collect test reports. SARIF and GitHub Actions annotations are already supported.
- **Better docs-site crawler examples**: add examples for checking locally built documentation sites, such as MkDocs, Sphinx, or static HTML output. Done when examples avoid live external services and can run deterministically.
- **Windows path coverage**: add tests for Windows-style local paths and file URLs. Done when path normalization behavior is explicit in fixtures.

## Completed

- Project configuration through `pyproject.toml` and `.linkchecker-py.toml`, with CLI overrides.
- GitHub Actions annotations, SARIF output, and strict unknown handling.
- Run-local HTTP deduplication, fragment-safe crawling, redirect-aware resolution, and bounded retries.
- Concurrency-safe per-host pacing with coalesced, paced `robots.txt` requests.
- Source-line propagation and robust local URL query, encoding, and directory handling.
