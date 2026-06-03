# Release Checklist

This project currently has a `v0.1.3` tag and package metadata for `0.1.3`. Use this checklist before the next release.

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

Recommended next tag after the existing `v0.1.3` tag:

```bash
git tag v0.1.4
git push origin v0.1.4
```

Use `v0.2.0` instead if the release adds new user-facing features rather than documentation or bug fixes.

## Publishing

The project is published on PyPI at https://pypi.org/project/linkchecker-py/ and on TestPyPI at https://test.pypi.org/project/linkchecker-py/.

## PyPI and TestPyPI setup

Before publishing for the first time, prefer Trusted Publishing over long-lived API tokens:

- On TestPyPI, add a pending GitHub publisher for:
  - PyPI project name: `linkchecker-py`
  - Owner: `jannis793`
  - Repository name: `linkchecker-py`
  - Workflow name: `publish.yml`
  - Environment name: `testpypi`
- On PyPI, add a pending GitHub publisher for:
  - PyPI project name: `linkchecker-py`
  - Owner: `jannis793`
  - Repository name: `linkchecker-py`
  - Workflow name: `publish.yml`
  - Environment name: `pypi`
- Run the `Publish` workflow manually with `target=testpypi`.
- Verify install from TestPyPI in a clean environment.
- Run the `Publish` workflow manually with `target=pypi`.
- Verify install from PyPI in a clean environment.

For fallback token publishing:

- Create or sign in to accounts at https://test.pypi.org/ and https://pypi.org/.
- Enable two-factor authentication on both accounts.
- Create a TestPyPI API token scoped to the `linkchecker-py` project after the first upload, or account-wide for the first upload only.
- Create a PyPI API token scoped to the `linkchecker-py` project after the first upload, or account-wide for the first upload only.
- Prefer replacing long-lived tokens with Trusted Publishing from this GitHub repository once the project exists on each index.

For local token publishing, export credentials without committing them:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-...
```

TestPyPI token dry run:

```bash
python -m twine upload --repository testpypi dist/*
```

PyPI token release:

```bash
python -m twine upload dist/*
```

Prefer PyPI Trusted Publishing from GitHub Actions before routine releases.
