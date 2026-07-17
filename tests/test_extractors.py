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
    assert [link.line for link in document.links] == [3, 4]


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


def test_extracts_markdown_source_lines(tmp_path: Path) -> None:
    doc = tmp_path / "README.md"
    doc.write_text("# Intro\n\n[one](one.md)\n\n<https://example.com>\n", encoding="utf-8")

    document = extract_links_from_file(doc)

    assert {link.url: link.line for link in document.links} == {
        "one.md": 3,
        "https://example.com": 5,
    }


def test_extracts_exact_lines_from_multiline_markdown_and_html_blocks(tmp_path: Path) -> None:
    doc = tmp_path / "README.md"
    doc.write_text(
        "[first](one.md) and\n[second](two.md)\n\n<div>\n<a href='three.html'>Three</a>\n</div>\n",
        encoding="utf-8",
    )

    document = extract_links_from_file(doc)

    assert {link.url: link.line for link in document.links} == {
        "one.md": 1,
        "two.md": 2,
        "three.html": 5,
    }


def test_nested_badge_urls_keep_their_actual_lines(tmp_path: Path) -> None:
    doc = tmp_path / "README.md"
    doc.write_text(
        "[![One](one.svg)](one.html)\n[![Two](two.svg)](two.html)\n",
        encoding="utf-8",
    )

    document = extract_links_from_file(doc)

    assert {link.url: link.line for link in document.links} == {
        "one.html": 1,
        "one.svg": 1,
        "two.html": 2,
        "two.svg": 2,
    }
