# Release Checklist

This project currently has a `v0.1.0` tag and package metadata for `0.1.0`. Use this checklist before the next release.

## Before tagging

- Confirm `src/linkchecker_py/_version.py` contains the intended version.
- Move relevant entries from `CHANGELOG.md` `Unreleased` into a dated release section.
- Run formatting, lint, tests, and build:

```bash
ruff check .
pytest
python -m build
```

- Inspect the generated artifacts:

```bash
python -m twine check dist/*
```

## Tagging

Recommended next tag after the existing `v0.1.0` tag:

```bash
git tag v0.1.1
git push origin v0.1.1
```

Use `v0.2.0` instead if the release adds new user-facing features rather than documentation or bug fixes.

## Publishing

The project is not currently documented here as published on PyPI. Do not add PyPI badges or install commands until the package exists there.

TestPyPI dry run:

```bash
python -m twine upload --repository testpypi dist/*
```

PyPI release:

```bash
python -m twine upload dist/*
```

Prefer PyPI Trusted Publishing from GitHub Actions before routine releases.
