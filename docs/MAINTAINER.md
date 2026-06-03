# Maintainer Notes

This document captures repo-local maintainer setup guidance. It is not evidence of external adoption.

## Recommended GitHub Labels

Use labels to make early project work easier to triage:

| Label | Purpose |
| --- | --- |
| `needs triage` | New issues or pull requests that need maintainer review. |
| `bug` | Reproducible broken behavior. |
| `enhancement` | New or expanded behavior. |
| `documentation` | README, examples, release docs, or maintainer docs. |
| `ci` | GitHub Actions, package checks, or deterministic automation. |
| `packaging` | PyPI metadata, build artifacts, entry points, or release workflows. |
| `good first issue` | Narrow, well-described contributor tasks. |
| `help wanted` | Scoped work where outside contribution would be useful. |
| `question` | Clarifications that are not yet bugs or features. |

Suggested colors if creating custom labels manually:

- `needs triage`: `FBCA04`
- `ci`: `5319E7`
- `packaging`: `D4C5F9`

## Triage Rhythm

- Check new issues for a minimal reproduction.
- Prefer offline fixtures over live websites in tests.
- Keep feature requests scoped to local docs and CI workflows until the project has real user feedback.
- Move broad ideas into `ROADMAP.md` instead of implying external demand.
