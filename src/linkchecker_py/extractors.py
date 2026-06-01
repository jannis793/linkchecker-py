from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

from markdown_it import MarkdownIt

from linkchecker_py.models import DocumentLinks, Link

SUPPORTED_SUFFIXES = {".md", ".markdown", ".mdown", ".mkd", ".html", ".htm"}


def slugify_heading(text: str) -> str:
    slug = re.sub(r"[^\w\- ]+", "", text.strip().lower(), flags=re.UNICODE)
    slug = re.sub(r"\s+", "-", slug)
    return slug.strip("-")


class _HTMLLinkParser(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.path = path
        self.links: list[Link] = []
        self.anchors: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value for name, value in attrs if value is not None}
        for anchor_attr in ("id", "name"):
            if attr_map.get(anchor_attr):
                self.anchors.add(unquote(attr_map[anchor_attr] or ""))
        for link_attr in ("href", "src"):
            url = attr_map.get(link_attr)
            if url:
                self.links.append(Link(url=url, source=self.path))


def extract_links_from_file(path: Path) -> DocumentLinks:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix in {".html", ".htm"}:
        return _extract_html(path, text)
    return _extract_markdown(path, text)


def extract_links_from_text(text: str, base: str) -> tuple[list[str], set[str]]:
    parser = _HTMLLinkParser(Path(base))
    parser.feed(text)
    return [link.url for link in parser.links], parser.anchors


def iter_supported_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(p for p in path.rglob("*") if p.suffix.lower() in SUPPORTED_SUFFIXES)
        elif path.suffix.lower() in SUPPORTED_SUFFIXES:
            files.append(path)
    return sorted(set(files))


def _extract_html(path: Path, text: str) -> DocumentLinks:
    parser = _HTMLLinkParser(path)
    parser.feed(text)
    return DocumentLinks(path=path, links=tuple(parser.links), anchors=frozenset(parser.anchors))


def _extract_markdown(path: Path, text: str) -> DocumentLinks:
    md = MarkdownIt("commonmark", {"html": True})
    tokens = md.parse(text)
    links: list[Link] = []
    anchors: set[str] = set()

    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            inline = tokens[index + 1] if index + 1 < len(tokens) else None
            if inline and inline.type == "inline":
                slug = slugify_heading(_plain_text(inline))
                if slug:
                    anchors.add(slug)
        if token.type == "inline" and token.children:
            for child in token.children:
                if child.type in {"link_open", "image"}:
                    href = child.attrGet("href") or child.attrGet("src")
                    if href:
                        line = token.map[0] + 1 if token.map else None
                        links.append(Link(url=href, source=path, line=line))
                if child.type == "html_inline":
                    html_links, html_anchors = extract_links_from_text(child.content, str(path))
                    links.extend(
                        Link(url=url, source=path, line=token.map[0] + 1 if token.map else None)
                        for url in html_links
                    )
                    anchors.update(html_anchors)
        if token.type == "html_block":
            html_links, html_anchors = extract_links_from_text(token.content, str(path))
            links.extend(
                Link(url=url, source=path, line=token.map[0] + 1 if token.map else None)
                for url in html_links
            )
            anchors.update(html_anchors)

    autolinks = re.findall(r"<(https?://[^>\s]+)>", text)
    known = {link.url for link in links}
    links.extend(Link(url=url, source=path) for url in autolinks if url not in known)
    return DocumentLinks(path=path, links=tuple(links), anchors=frozenset(anchors))


def _plain_text(token: object) -> str:
    children = getattr(token, "children", None) or []
    return "".join(getattr(child, "content", "") for child in children)
