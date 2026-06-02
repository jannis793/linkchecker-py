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

## Release Process

Release steps are documented in [docs/RELEASE.md](docs/RELEASE.md). Publishing to PyPI or TestPyPI should only happen after the release checklist passes and the target package name is confirmed.
