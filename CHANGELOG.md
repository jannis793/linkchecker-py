# Changelog

All notable changes to `linkchecker-py` will be documented in this file.

The project follows semantic versioning once releases are published.

## Unreleased

- Dogfood `linkchecker-py` in CI against this repository's README, docs, and examples.
- Add 60-second onboarding, clearer examples output, starter issue guidance, maintainer labels, and triage documentation.
- Reuse crawl responses and deduplicate run-local HTTP requests while preserving source occurrences and fragment validation.
- Resolve discovered links against final redirect URLs and retain URL fragments during site crawls.
- Add concurrency-safe per-host pacing, coalesced paced `robots.txt` requests, and configurable bounded retries for transient failures.
- Propagate source line numbers through terminal, JSON, Markdown, GitHub Actions annotation, and SARIF output.
- Correct local URL query, percent-encoding, same-document, and directory handling.
- Add project TOML configuration with CLI override precedence and strict `--fail-on unknown` behavior.

## 0.1.3 - 2026-06-03

- Add manual Trusted Publishing workflow for TestPyPI and PyPI.
- Prefer pending Trusted Publisher setup in release documentation.

## 0.1.2 - 2026-06-03

- Add local Markdown/HTML examples and an adaptable GitHub Actions link-check workflow.
- Document first-time PyPI and TestPyPI credential setup.
- Fix same-document fragment checks when the source path is relative.

## 0.1.1 - 2026-06-02

- Improve open-source maintainer documentation, release guidance, and issue workflow files.
- Include unknown results in Markdown report summaries and escape Markdown table cells.
- Keep runtime version metadata in one package module and expose it as `linkchecker_py.__version__`.

## 0.1.0 - 2026-06-01

- Add async Markdown, HTML, and website link checking.
- Add local file and fragment validation.
- Add same-origin website crawling with depth limits.
- Add JSON and Markdown reports.
- Add optional remote result caching.
- Add `robots.txt`, concurrency, rate-limit, and exclude controls.
