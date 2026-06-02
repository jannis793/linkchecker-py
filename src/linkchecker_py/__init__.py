"""Async link checking toolkit for Markdown, HTML, and websites."""

from linkchecker_py._version import __version__
from linkchecker_py.checker import CheckOptions, LinkChecker
from linkchecker_py.models import LinkResult, LinkStatus

__all__ = ["CheckOptions", "LinkChecker", "LinkResult", "LinkStatus", "__version__"]
