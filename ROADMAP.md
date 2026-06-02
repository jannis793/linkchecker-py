# Roadmap

`linkchecker-py` is early and intentionally scoped. The near-term goal is to make local and CI link checks reliable for documentation repositories without pretending to be a full web crawler.

## Near term

- Add a project-level configuration file for common excludes, concurrency, cache, and report settings.
- Add SARIF output so broken links can appear in GitHub code scanning.
- Add per-host rate-limit settings for mixed documentation and API-reference sites.
- Improve Markdown anchor compatibility for documentation systems with custom slug rules.
- Add more report-focused tests around escaping, source paths, and unknown results.

## Later

- Add persistent crawl manifests for larger documentation sites.
- Add optional authentication/header configuration for private documentation.
- Add release automation once PyPI publishing is configured.

## Suggested starter issues

- Document examples for popular static site generators.
- Add a `--fail-on unknown` option for stricter CI workflows.
- Add a JSON schema for report output.
- Add tests for Windows-style local paths.
