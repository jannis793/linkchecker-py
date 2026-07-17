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


def unique_anchor(slug: str, anchors: set[str]) -> str:
    if slug not in anchors:
        return slug
    index = 1
    while f"{slug}-{index}" in anchors:
        index += 1
    return f"{slug}-{index}"


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
                self.links.append(Link(url=url, source=self.path, line=self.getpos()[0]))


def extract_links_from_file(path: Path) -> DocumentLinks:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix in {".html", ".htm"}:
        return _extract_html(path, text)
    return _extract_markdown(path, text)


def extract_links_from_text(text: str, base: str) -> tuple[list[str], set[str]]:
    parser = _parse_html(text, Path(base))
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
                    anchors.add(unique_anchor(slug, anchors))
        if token.type == "inline" and token.children:
            source_text, source_line = _token_source(text, token.map)
            search_offsets: dict[str, int] = {}
            for child in token.children:
                if child.type in {"link_open", "image"}:
                    href = child.attrGet("href") or child.attrGet("src")
                    if href:
                        line, search_offsets[href] = _find_line(
                            source_text,
                            href,
                            source_line,
                            search_offsets.get(href, 0),
                        )
                        links.append(Link(url=href, source=path, line=line))
                if child.type == "html_inline":
                    parser = _parse_html(child.content, path)
                    html_line, search_offsets[child.content] = _find_line(
                        source_text,
                        child.content,
                        source_line,
                        search_offsets.get(child.content, 0),
                    )
                    links.extend(
                        Link(
                            url=link.url,
                            source=path,
                            line=(html_line or 1) + (link.line or 1) - 1,
                        )
                        for link in parser.links
                    )
                    anchors.update(parser.anchors)
        if token.type == "html_block":
            parser = _parse_html(token.content, path)
            block_line = token.map[0] + 1 if token.map else 1
            links.extend(
                Link(
                    url=link.url,
                    source=path,
                    line=block_line + (link.line or 1) - 1,
                )
                for link in parser.links
            )
            anchors.update(parser.anchors)

    autolinks = re.finditer(r"<(https?://[^>\s]+)>", text)
    known = {link.url for link in links}
    links.extend(
        Link(url=match.group(1), source=path, line=text.count("\n", 0, match.start()) + 1)
        for match in autolinks
        if match.group(1) not in known
    )
    return DocumentLinks(path=path, links=tuple(links), anchors=frozenset(anchors))


def _plain_text(token: object) -> str:
    children = getattr(token, "children", None) or []
    return "".join(getattr(child, "content", "") for child in children)


def _parse_html(text: str, path: Path) -> _HTMLLinkParser:
    parser = _HTMLLinkParser(path)
    parser.feed(text)
    return parser


def _token_source(text: str, token_map: list[int] | None) -> tuple[str, int | None]:
    if not token_map:
        return "", None
    lines = text.splitlines(keepends=True)
    return "".join(lines[token_map[0] : token_map[1]]), token_map[0] + 1


def _find_line(
    source_text: str,
    url: str,
    start_line: int | None,
    search_offset: int,
) -> tuple[int | None, int]:
    position = source_text.find(url, search_offset)
    if position < 0:
        return start_line, search_offset
    line = (start_line or 1) + source_text.count("\n", 0, position)
    return line, position + len(url)
