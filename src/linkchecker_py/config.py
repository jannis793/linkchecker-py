from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass(frozen=True)
class ProjectConfig:
    exclude: list[str] = field(default_factory=list)
    concurrency: int = 20
    rate_limit: float = 0.0
    cache: bool = False
    report: Path | None = None
    respect_robots: bool = True
    retries: int = 2
    retry_backoff: float = 0.25
    fail_on: str = "broken"
    github_annotations: bool = False


def load_config(path: Path | None = None, start: Path | None = None) -> ProjectConfig:
    config_path = path or discover_config(start or Path.cwd())
    if config_path is None:
        return ProjectConfig()
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)
    if config_path.name == "pyproject.toml":
        data = data.get("tool", {}).get("linkchecker-py", {})
    elif "linkchecker-py" in data:
        data = data["linkchecker-py"]
    if not isinstance(data, dict):
        raise ValueError(f"invalid linkchecker-py config in {config_path}")
    return _parse_config(data, config_path.parent)


def discover_config(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        dedicated = directory / ".linkchecker-py.toml"
        if dedicated.is_file():
            return dedicated
        pyproject = directory / "pyproject.toml"
        if pyproject.is_file():
            with pyproject.open("rb") as handle:
                data = tomllib.load(handle)
            if isinstance(data.get("tool", {}).get("linkchecker-py"), dict):
                return pyproject
    return None


def _parse_config(data: dict[str, Any], base: Path) -> ProjectConfig:
    known = {field.name for field in ProjectConfig.__dataclass_fields__.values()}
    unknown = sorted(set(data) - known)
    if unknown:
        raise ValueError(f"unknown config option(s): {', '.join(unknown)}")
    values = dict(data)
    _validate_types(values)
    if "report" in values and values["report"] is not None:
        report = Path(values["report"])
        values["report"] = report if report.is_absolute() else base / report
    config = ProjectConfig(**values)
    if config.concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    if config.rate_limit < 0:
        raise ValueError("rate_limit cannot be negative")
    if config.retries < 0:
        raise ValueError("retries cannot be negative")
    if config.retry_backoff < 0:
        raise ValueError("retry_backoff cannot be negative")
    if config.fail_on not in {"broken", "unknown"}:
        raise ValueError("fail_on must be 'broken' or 'unknown'")
    return config


def _validate_types(values: dict[str, Any]) -> None:
    if "exclude" in values and (
        not isinstance(values["exclude"], list)
        or not all(isinstance(item, str) for item in values["exclude"])
    ):
        raise ValueError("exclude must be an array of strings")
    if "concurrency" in values and type(values["concurrency"]) is not int:
        raise ValueError("concurrency must be an integer")
    if "retries" in values and type(values["retries"]) is not int:
        raise ValueError("retries must be an integer")
    for name in ("rate_limit", "retry_backoff"):
        if name in values and (
            isinstance(values[name], bool) or not isinstance(values[name], (int, float))
        ):
            raise ValueError(f"{name} must be a number")
    for name in ("cache", "respect_robots", "github_annotations"):
        if name in values and type(values[name]) is not bool:
            raise ValueError(f"{name} must be a boolean")
    if (
        "report" in values
        and values["report"] is not None
        and not isinstance(values["report"], str)
    ):
        raise ValueError("report must be a path string")
    if "fail_on" in values and not isinstance(values["fail_on"], str):
        raise ValueError("fail_on must be a string")
