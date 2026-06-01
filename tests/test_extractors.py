from pathlib import Path

from linkchecker_py.extractors import extract_links_from_file


def test_extracts_markdown_links_images_and_headings(tmp_path: Path) -> None:
    doc = tmp_path / "README.md"
    doc.write_text(
        """
# Intro Section

[site](https://example.com/docs#top)
![logo](assets/logo.png)
[local](guide.md#install)
<https://example.org/plain>
""",
        encoding="utf-8",
    )

    document = extract_links_from_file(doc)

    assert {link.url for link in document.links} == {
        "https://example.com/docs#top",
        "assets/logo.png",
        "guide.md#install",
        "https://example.org/plain",
    }
    assert "intro-section" in document.anchors


def test_extracts_html_links_images_and_element_ids(tmp_path: Path) -> None:
    page = tmp_path / "index.html"
    page.write_text(
        """
<h2 id="overview">Overview</h2>
<a href="/docs#overview">Docs</a>
<img src="hero.png" alt="Hero">
""",
        encoding="utf-8",
    )

    document = extract_links_from_file(page)

    assert {link.url for link in document.links} == {"/docs#overview", "hero.png"}
    assert "overview" in document.anchors


def test_extracts_github_style_duplicate_heading_anchors(tmp_path: Path) -> None:
    doc = tmp_path / "README.md"
    doc.write_text(
        """
# Install

## Install

## Install
""",
        encoding="utf-8",
    )

    document = extract_links_from_file(doc)

    assert {"install", "install-1", "install-2"} <= document.anchors
