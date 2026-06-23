#!/usr/bin/env python3
"""Build or scaffold AGILANG mobile native runtime artifacts.

This script is CI-friendly. It writes target manifests and, when the required
Android/iOS compiler toolchain is available, can be extended to compile the
AGILANG C runtime for mobile platforms.
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

TARGETS = {
    "android-arm64-v8a": {"library_name": "libagilang_net_runtime.so", "toolchain": "Android NDK + CMake"},
    "android-x86_64": {"library_name": "libagilang_net_runtime.so", "toolchain": "Android NDK + CMake"},
    "ios-arm64": {"library_name": "libagilang_net_runtime.a", "toolchain": "Xcode clang"},
    "ios-simulator-arm64": {"library_name": "libagilang_net_runtime.a", "toolchain": "Xcode clang"},
    "ios-simulator-x86_64": {"library_name": "libagilang_net_runtime.a", "toolchain": "Xcode clang"},
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=list(TARGETS) + ["all"], default="all")
    parser.add_argument("--out-root", default="agilang/native/prebuilt")
    args = parser.parse_args()
    root = Path(args.out_root)
    selected = TARGETS if args.target == "all" else {args.target: TARGETS[args.target]}
    for tag, meta in selected.items():
        out = root / tag
        out.mkdir(parents=True, exist_ok=True)
        payload = {
            "platform_tag": tag,
            "runtime_version": "1.5.0",
            "build_host_platform": platform.platform(),
            "toolchain": meta["toolchain"],
            "expected_library": meta["library_name"],
            "status": "manifest-only-until-mobile-toolchain-builds-artifact",
            "notes": "Use Android NDK/Xcode CI jobs to generate the physical binary for this platform.",
        }
        (out / "manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        (out / "README.md").write_text(f"# {tag}\n\nExpected artifact: `{meta['library_name']}`.\n\n{payload['notes']}\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
