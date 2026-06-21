#!/usr/bin/env python3
"""Build AGILANG native runtime prebuilt artifacts for the current platform."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import platform
import shutil
import subprocess
from pathlib import Path


def platform_tag() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower().replace("amd64", "x86_64")
    if machine in {"x64", "x86-64"}:
        machine = "x86_64"
    if system.startswith("linux"):
        return f"linux-{machine}"
    if system == "darwin":
        return f"macos-{machine}"
    if system.startswith("win"):
        return f"windows-{machine}"
    return f"{system}-{machine}"


def shared_name() -> str:
    system = platform.system().lower()
    if system.startswith("win"):
        return "agilang_net_runtime.dll"
    if system == "darwin":
        return "libagilang_net_runtime.dylib"
    return "libagilang_net_runtime.so"


def static_name() -> str:
    return "agilang_net_runtime.lib" if platform.system().lower().startswith("win") else "libagilang_net_runtime.a"


def compiler() -> str:
    return shutil.which("gcc") or shutil.which("clang") or "gcc"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None, help="Output root. Defaults to agilang/native/prebuilt/<platform-tag>.")
    parser.add_argument("--cc", default=None, help="C compiler command, for example gcc or clang.")
    parser.add_argument("--copy-root-native", action="store_true", help="Also mirror artifacts to native/prebuilt/<platform-tag>.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    src = root / "agilang" / "native" / "agilang_net_runtime.c"
    out_dir = Path(args.out) if args.out else root / "agilang" / "native" / "prebuilt" / platform_tag()
    out_dir.mkdir(parents=True, exist_ok=True)
    cc = args.cc or compiler()
    system = platform.system().lower()
    shared = out_dir / shared_name()
    obj = out_dir / "agilang_net_runtime.o"
    static = out_dir / static_name()

    if system.startswith("win"):
        run([cc, "-std=c11", "-O2", "-Wall", "-Wextra", str(src), "-shared", "-o", str(shared), "-lws2_32"])
        run([cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-c", str(src), "-o", str(obj)])
        # ar may not exist on all Windows toolchains; keep DLL as the primary prebuilt.
        ar = shutil.which("ar")
        if ar:
            run([ar, "rcs", str(static), str(obj)])
    else:
        run([cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-fPIC", "-shared", str(src), "-o", str(shared), "-pthread"])
        run([cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-fPIC", "-c", str(src), "-o", str(obj)])
        run(["ar", "rcs", str(static), str(obj)])

    meta = {
        "platform_tag": platform_tag(),
        "compiler": cc,
        "build_host_platform": platform.platform(),
        "artifacts": {},
    }
    for path in sorted(out_dir.iterdir()):
        if path.is_file() and path.name != "manifest.json":
            meta["artifacts"][path.name] = {"size_bytes": path.stat().st_size, "sha256": sha256(path)}
    lib = ctypes.CDLL(str(shared.resolve()))
    lib.agi_net_runtime_version.restype = ctypes.c_char_p
    lib.agi_net_runtime_capabilities.restype = ctypes.c_char_p
    lib.agi_net_runtime_selftest.restype = ctypes.c_int
    meta["runtime_version"] = lib.agi_net_runtime_version().decode("utf-8")
    meta["selftest"] = int(lib.agi_net_runtime_selftest()) == 0
    meta["capabilities"] = json.loads(lib.agi_net_runtime_capabilities().decode("utf-8"))
    (out_dir / "manifest.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    if args.copy_root_native:
        mirror = root / "native" / "prebuilt" / platform_tag()
        if mirror.resolve() != out_dir.resolve():
            mirror.mkdir(parents=True, exist_ok=True)
            for item in out_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, mirror / item.name)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
