# Examples

These fixtures are small enough to run locally and are intended to show how `linkchecker-py` behaves against Markdown, HTML, local files, anchors, skipped schemes, and intentionally broken links.

## Try it locally

From the repository root after installing the project:

```bash
python -m pip install -e .
linkchecker-py files examples/site --report examples/link-report.md
```

The command is expected to exit with `1` because `examples/site/index.md` contains one intentionally broken local link:

```markdown
[Missing page](missing.md)
```

For a passing run, exclude the intentionally broken fixture:

```bash
linkchecker-py files examples/site \
  --exclude "missing.md" \
  --report examples/link-report.md
```

You can also inspect the HTML fixture directly:

```bash
linkchecker-py files examples/site/page.html
```

## CI example

See [github-actions-link-check.yml](github-actions-link-check.yml) for a workflow another repository can adapt by installing `linkchecker-py` from PyPI.
