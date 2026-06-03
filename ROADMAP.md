# Roadmap

`linkchecker-py` is early and intentionally scoped. The near-term goal is to make local and CI link checks reliable for documentation repositories without pretending to be a full web crawler.

## Near term

- Add a project-level configuration file for common excludes, concurrency, cache, and report settings.
- Add GitHub annotation output for pull request logs.
- Add SARIF output so broken links can appear in GitHub code scanning.
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

- **Config file support**: add `pyproject.toml` or `.linkchecker-py.toml` support for excludes, concurrency, rate limit, cache, report path, and robots behavior. Done when CLI flags still override config values and tests cover config discovery.
- **GitHub annotation output**: add an output mode that prints `::error file=...,line=...::...` for broken links in Actions logs. Done when annotations include the source path and existing report formats still work.
- **SARIF or JUnit report support**: add one CI-native report format beyond JSON and Markdown. Done when the report can be uploaded by GitHub Actions or common CI test-report collectors.
- **Better docs-site crawler examples**: add examples for checking locally built documentation sites, such as MkDocs, Sphinx, or static HTML output. Done when examples avoid live external services and can run deterministically.
- **Strict unknown handling**: add a `--fail-on unknown` option for teams that want inconclusive links to fail CI. Done when exit-code behavior is documented and tested.
- **Windows path coverage**: add tests for Windows-style local paths and file URLs. Done when path normalization behavior is explicit in fixtures.
