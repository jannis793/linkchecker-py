# Contributing

Thanks for helping improve `linkchecker-py`.

## Development Setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Quality Checks

Run these before opening a pull request:

```bash
ruff check .
pytest
python -m build
```

## Pull Request Guidelines

- Keep changes focused and explain the user-facing behavior.
- Add or update tests for new link parsing, checking, crawling, or reporting behavior.
- Mock network traffic in tests. The test suite should be deterministic and offline.
- Update the README when CLI flags or report formats change.
- Update `CHANGELOG.md` for user-facing changes.
- Run the CI-equivalent checks locally when possible.

## Issue Reports

Helpful bug reports include:

- The command you ran.
- A minimal Markdown, HTML, or URL example.
- Expected behavior and actual behavior.
- Python version and operating system.

## Good First Issues

Good first issues should be small, reproducible, and mostly local to one area of the project. Examples include:

- Adding a focused parser or report-format test.
- Improving an example fixture or README command.
- Documenting one CLI option more clearly.
- Fixing a small Markdown or HTML edge case with a regression test.

Avoid labeling work as `good first issue` if it requires live network credentials, release publishing, broad crawler changes, or unclear product decisions.

## Maintainer Triage Checklist

When reviewing a new issue or pull request:

- Reproduce the reported command or identify the missing fixture.
- Classify the work as `bug`, `enhancement`, `documentation`, `ci`, or `packaging`.
- Add `needs triage` until scope and next steps are clear.
- Mark `good first issue` only when the change is narrow and well described.
- Ask for a minimal Markdown, HTML, or URL example when behavior is ambiguous.
- Confirm tests remain deterministic and do not depend on live external services.
- Note whether README, examples, changelog, or release docs need updates.

Recommended labels and maintainer setup notes are documented in [docs/MAINTAINER.md](docs/MAINTAINER.md).

## Release Process

Release steps are documented in [docs/RELEASE.md](docs/RELEASE.md). Publishing to PyPI or TestPyPI should only happen after the release checklist passes and the target package name is confirmed.
