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
```

## Pull Request Guidelines

- Keep changes focused and explain the user-facing behavior.
- Add or update tests for new link parsing, checking, crawling, or reporting behavior.
- Mock network traffic in tests. The test suite should be deterministic and offline.
- Update the README when CLI flags or report formats change.

## Issue Reports

Helpful bug reports include:

- The command you ran.
- A minimal Markdown, HTML, or URL example.
- Expected behavior and actual behavior.
- Python version and operating system.
