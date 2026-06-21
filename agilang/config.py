"""Project configuration helpers for AGILANG."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    tomllib = None  # type: ignore


@dataclass(frozen=True)
class ProjectConfig:
    root: Path
    name: str = "agilang-project"
    version: str = "0.1.0"
    entry: str = "src/main.agi"

    @property
    def entry_path(self) -> Path:
        return (self.root / self.entry).resolve()


def find_project_root(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    while True:
        cfg = current / "agilang.toml"
        if cfg.exists():
            return current
        if current.parent == current:
            return None
        current = current.parent


def load_project_config(root: Path | None = None) -> ProjectConfig | None:
    project_root = root or find_project_root()
    if project_root is None:
        return None
    cfg_path = project_root / "agilang.toml"
    data: dict = {}
    if cfg_path.exists():
        raw = cfg_path.read_bytes()
        if tomllib is not None:
            data = tomllib.loads(raw.decode("utf-8"))
        else:
            # Minimal fallback parser for the generated agilang.toml shape.
            section = None
            data = {}
            for line in raw.decode("utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1].strip()
                    data.setdefault(section, {})
                    continue
                if "=" in line and section:
                    key, value = line.split("=", 1)
                    data[section][key.strip()] = value.strip().strip('"').strip("'")
    project = data.get("project", {}) if isinstance(data, dict) else {}
    return ProjectConfig(
        root=project_root.resolve(),
        name=str(project.get("name", project_root.name)),
        version=str(project.get("version", "0.1.0")),
        entry=str(project.get("entry", "src/main.agi")),
    )
