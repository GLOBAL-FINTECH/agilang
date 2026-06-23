"""AGILANG package manager utilities.

The package manager is intentionally local-first for v0.6. It edits
`agilang.toml`, creates a deterministic lock file, and vendors local/path/git
references into `.agilang/deps` metadata. A real registry can be added later
without changing project manifests.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .config import find_project_root, load_project_config

try:
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore


@dataclass
class PackageManifest:
    root: Path
    project: dict[str, str] = field(default_factory=dict)
    dependencies: dict[str, str] = field(default_factory=dict)

    @property
    def path(self) -> Path:
        return self.root / "agilang.toml"

    @property
    def lock_path(self) -> Path:
        return self.root / "agilang.lock"

    def write(self) -> None:
        lines = ["[project]"]
        for k in ["name", "version", "entry"]:
            if k in self.project:
                lines.append(f'{k} = "{self.project[k]}"')
        lines.append("")
        lines.append("[dependencies]")
        for name, spec in sorted(self.dependencies.items()):
            lines.append(f'{name} = "{spec}"')
        lines.append("")
        self.path.write_text("\n".join(lines), encoding="utf-8")

    def write_lock(self) -> None:
        payload = {
            "version": 1,
            "project": self.project,
            "dependencies": [{"name": k, "source": v} for k, v in sorted(self.dependencies.items())],
        }
        self.lock_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _parse_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    raw = path.read_bytes()
    if tomllib is not None:
        return tomllib.loads(raw.decode("utf-8"))
    data: dict[str, dict[str, str]] = {}
    section = None
    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            data[section] = {}
        elif section and "=" in line:
            k, v = line.split("=", 1)
            data[section][k.strip()] = v.strip().strip('"').strip("'")
    return data


def load_manifest(root: Path | None = None) -> PackageManifest:
    project_root = root or find_project_root() or Path.cwd().resolve()
    data = _parse_toml(project_root / "agilang.toml")
    return PackageManifest(
        root=project_root,
        project={k: str(v) for k, v in data.get("project", {}).items()},
        dependencies={k: str(v) for k, v in data.get("dependencies", {}).items()},
    )


def init_project(name: str | None = None, root: Path | None = None) -> PackageManifest:
    project_root = (root or Path.cwd()).resolve()
    (project_root / "src").mkdir(parents=True, exist_ok=True)
    manifest = PackageManifest(
        root=project_root,
        project={"name": name or project_root.name, "version": "0.1.0", "entry": "src/main.agi"},
        dependencies={},
    )
    if not (project_root / "src" / "main.agi").exists():
        (project_root / "src" / "main.agi").write_text('fn main() -> i32:\n    print("Hello from AGILANG")\n    return 0\n', encoding="utf-8")
    manifest.write()
    manifest.write_lock()
    return manifest


def add_dependency(name: str, spec: str, root: Path | None = None) -> PackageManifest:
    manifest = load_manifest(root)
    manifest.dependencies[name] = spec
    manifest.write()
    manifest.write_lock()
    return manifest


def remove_dependency(name: str, root: Path | None = None) -> PackageManifest:
    manifest = load_manifest(root)
    manifest.dependencies.pop(name, None)
    manifest.write()
    manifest.write_lock()
    return manifest


def install_dependencies(root: Path | None = None) -> list[Path]:
    manifest = load_manifest(root)
    deps_root = manifest.root / ".agilang" / "deps"
    deps_root.mkdir(parents=True, exist_ok=True)
    installed: list[Path] = []
    for name, spec in sorted(manifest.dependencies.items()):
        meta = deps_root / f"{name}.json"
        payload = {"name": name, "source": spec, "status": "recorded"}
        if spec.startswith("path:"):
            src = (manifest.root / spec[5:]).resolve()
            payload["resolved_path"] = str(src)
            payload["status"] = "linked" if src.exists() else "missing"
        elif spec.startswith("git+"):
            payload["status"] = "git-reference-recorded"
        meta.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        installed.append(meta)
    manifest.write_lock()
    return installed


def list_dependencies(root: Path | None = None) -> str:
    manifest = load_manifest(root)
    if not manifest.dependencies:
        return "No dependencies declared."
    return "\n".join(f"{name}: {spec}" for name, spec in sorted(manifest.dependencies.items()))


def pack_project(root: Path | None = None, out: Path | None = None) -> Path:
    manifest = load_manifest(root)
    name = manifest.project.get("name", manifest.root.name)
    version = manifest.project.get("version", "0.1.0")
    target = out or (manifest.root / "dist" / f"{name}-{version}.agipkg")
    target.parent.mkdir(parents=True, exist_ok=True)
    base = target.with_suffix("")
    if base.exists():
        shutil.rmtree(base)
    shutil.make_archive(str(base), "zip", manifest.root)
    zip_path = base.with_suffix(".zip")
    if target.exists():
        target.unlink()
    zip_path.rename(target)
    return target
