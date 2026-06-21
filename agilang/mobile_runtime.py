"""AGILANG v1.7 mobile native runtime bridge support.

This module provides the production bridge layer needed for mobile apps:

- React Native/Expo client support remains the primary mobile application path.
- Android and iOS native bridge targets are generated so mobile apps can link
  the AGILANG C networking runtime when the platform toolchain is available.
- Build metadata distinguishes source/CI support from physically bundled
  binaries, just like the desktop/server prebuilt runtime matrix.
"""

from __future__ import annotations

import json
import platform
import shutil
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MOBILE_RUNTIME_VERSION = "1.7.0"

MOBILE_NATIVE_TARGETS: dict[str, dict[str, Any]] = {
    "android-arm64-v8a": {
        "os": "android",
        "abi": "arm64-v8a",
        "library_name": "libagilang_net_runtime.so",
        "toolchain": "Android NDK + CMake",
        "ci_runner": "ubuntu-latest",
        "status": "source-and-ci-supported",
        "notes": "Builds a shared library for modern 64-bit Android devices through the Android NDK.",
    },
    "android-x86_64": {
        "os": "android",
        "abi": "x86_64",
        "library_name": "libagilang_net_runtime.so",
        "toolchain": "Android NDK + CMake",
        "ci_runner": "ubuntu-latest",
        "status": "source-and-ci-supported",
        "notes": "Builds a shared library for Android emulators and x86_64 Android targets.",
    },
    "ios-arm64": {
        "os": "ios",
        "abi": "arm64",
        "library_name": "libagilang_net_runtime.a",
        "toolchain": "Xcode clang + Swift bridge",
        "ci_runner": "macos-latest",
        "status": "source-and-ci-supported",
        "notes": "Builds a static library for physical iPhone/iPad devices.",
    },
    "ios-simulator-arm64": {
        "os": "ios",
        "abi": "arm64-simulator",
        "library_name": "libagilang_net_runtime.a",
        "toolchain": "Xcode clang + Swift bridge",
        "ci_runner": "macos-latest",
        "status": "source-and-ci-supported",
        "notes": "Builds a static library for Apple Silicon iOS Simulator.",
    },
    "ios-simulator-x86_64": {
        "os": "ios",
        "abi": "x86_64-simulator",
        "library_name": "libagilang_net_runtime.a",
        "toolchain": "Xcode clang + Swift bridge",
        "ci_runner": "macos-13",
        "status": "source-and-ci-supported",
        "notes": "Builds a static library for Intel iOS Simulator where available.",
    },
}


def _package_native_dir() -> Path:
    return Path(__file__).resolve().parent / "native"


def _mobile_prebuilt_dir(tag: str) -> Path:
    return _package_native_dir() / "prebuilt" / tag


def mobile_runtime_matrix() -> dict[str, Any]:
    """Return Android/iOS bridge targets and artifact availability."""
    targets: dict[str, Any] = {}
    for tag, meta in MOBILE_NATIVE_TARGETS.items():
        base = _mobile_prebuilt_dir(tag)
        expected = base / meta["library_name"]
        manifest = base / "manifest.json"
        artifacts = {p.name: str(p) for p in sorted(base.iterdir()) if p.is_file()} if base.exists() else {}
        targets[tag] = {
            **meta,
            "prebuilt_dir": str(base),
            "expected_library": str(expected),
            "library_bundled": expected.exists(),
            "manifest_bundled": manifest.exists(),
            "artifacts": artifacts,
        }
    return {
        "agilang_mobile_runtime_version": MOBILE_RUNTIME_VERSION,
        "host_platform": platform.platform(),
        "mobile_support_model": "React Native/Expo app + optional native AGILANG C runtime bridge",
        "targets": targets,
        "important_note": "Android/iOS binaries are produced by platform toolchains/CI. This package includes bridge source and release wiring; it does not fake mobile binaries on non-mobile build hosts.",
    }


def mobile_runtime_capabilities() -> dict[str, Any]:
    return {
        "react_native_expo_client": True,
        "react_web_client": True,
        "typescript_realtime_sdk": True,
        "android_native_bridge_source": True,
        "android_ndk_cmake_target": True,
        "ios_swift_bridge_source": True,
        "ios_static_library_target": True,
        "websocket_client": True,
        "webrtc_signaling_client": True,
        "native_media_engine": False,
        "notes": [
            "AGILANG mobile apps are generated as React Native/Expo clients.",
            "The native bridge lets mobile apps link the AGILANG C HTTP/WebSocket runtime where the platform toolchain permits it.",
            "Full WebRTC media remains handled by platform/browser WebRTC APIs; AGILANG provides signaling and realtime integration.",
        ],
    }


def mobile_runtime_doctor() -> dict[str, Any]:
    """Report local mobile build tool availability."""
    return {
        "host_platform": platform.platform(),
        "python": platform.python_version(),
        "tools": {
            "node": shutil.which("node"),
            "npm": shutil.which("npm"),
            "expo": shutil.which("expo"),
            "cmake": shutil.which("cmake"),
            "ninja": shutil.which("ninja"),
            "xcodebuild": shutil.which("xcodebuild"),
            "xcrun": shutil.which("xcrun"),
            "pod": shutil.which("pod"),
        },
        "targets": list(MOBILE_NATIVE_TARGETS),
        "capabilities": mobile_runtime_capabilities(),
    }


def _safe_slug(name: str) -> str:
    import re
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name.strip()).strip("-").lower()
    return slug or "agilang-mobile-app"


def _write(path: Path, content: str, files: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")
    files.append(path)


@dataclass
class MobileBridgeResult:
    root: Path
    target: str
    files: list[Path]

    def as_dict(self) -> dict[str, Any]:
        return {"root": str(self.root), "target": self.target, "files": [str(f) for f in self.files]}


def create_mobile_native_bridge(
    name: str,
    *,
    directory: str | Path | None = None,
    target: str = "both",
    force: bool = False,
) -> MobileBridgeResult:
    """Create Android/iOS native bridge source for an AGILANG mobile client."""
    target = target.lower()
    if target not in {"android", "ios", "both"}:
        raise ValueError("target must be android, ios, or both")
    parent = Path(directory).expanduser().resolve() if directory else Path.cwd().resolve()
    root = parent / _safe_slug(name)
    if root.exists() and any(root.iterdir()) and not force:
        raise FileExistsError(f"Directory exists and is not empty: {root}")
    files: list[Path] = []

    _write(root / "README.md", f"""
# {name} AGILANG Mobile Native Bridge

This bridge connects a React Native/Expo mobile app to the AGILANG native C networking runtime.

## Supported mobile targets

- Android arm64-v8a
- Android x86_64 emulator
- iOS arm64 device
- iOS Simulator arm64 / x86_64

## Important

This is bridge/source support. Android builds require Android NDK + CMake. iOS builds require Xcode command-line tools.
The normal mobile app remains React Native/Expo; this bridge is for native transport acceleration and local runtime capability checks.
""", files)

    _write(root / "runtime/mobile-runtime.json", json.dumps(mobile_runtime_matrix(), indent=2), files)

    if target in {"android", "both"}:
        _write(root / "android/agilang-runtime/CMakeLists.txt", r"""
cmake_minimum_required(VERSION 3.18)
project(agilang_mobile_runtime C)

add_library(agilang_net_runtime SHARED
    ../../native/agilang_net_runtime.c
)

target_compile_features(agilang_net_runtime PRIVATE c_std_11)
target_compile_options(agilang_net_runtime PRIVATE -Wall -Wextra -O2)
target_include_directories(agilang_net_runtime PUBLIC ../../native)
""", files)
        _write(root / "android/agilang-runtime/build.gradle", r"""
plugins {
    id 'com.android.library'
}

android {
    namespace 'com.agilang.runtime'
    compileSdk 35

    defaultConfig {
        minSdk 23
        externalNativeBuild {
            cmake {
                arguments '-DANDROID_STL=c++_shared'
            }
        }
    }

    externalNativeBuild {
        cmake {
            path 'CMakeLists.txt'
        }
    }
}
""", files)
        _write(root / "android/agilang-runtime/src/main/AndroidManifest.xml", """<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\" />\n""", files)
        _write(root / "android/agilang-runtime/src/main/java/com/agilang/runtime/AgilangRuntimeModule.kt", r"""
package com.agilang.runtime

object AgilangRuntimeModule {
    init {
        try { System.loadLibrary("agilang_net_runtime") } catch (_: Throwable) {}
    }
    external fun nativeVersion(): String
    external fun nativeCapabilities(): String
    external fun nativeSelftest(): Int
}
""", files)
        _write(root / "android/README.md", r"""
# Android AGILANG Runtime Bridge

Use this folder as an Android library module or copy `android/agilang-runtime` into an existing React Native Android project.

Build requirements:

- Android SDK
- Android NDK
- CMake
- Gradle / Android Gradle Plugin

Expected artifact names:

- `libagilang_net_runtime.so` for `arm64-v8a`
- `libagilang_net_runtime.so` for `x86_64`
""", files)

    if target in {"ios", "both"}:
        _write(root / "ios/AgilangRuntimeBridge.swift", r"""
import Foundation

public final class AgilangRuntimeBridge {
    public init() {}

    public func runtimeVersion() -> String {
        guard let ptr = agi_net_runtime_version() else { return "unknown" }
        return String(cString: ptr)
    }

    public func capabilitiesJSON() -> String {
        guard let ptr = agi_net_runtime_capabilities() else { return "{}" }
        return String(cString: ptr)
    }

    public func selftest() -> Bool {
        return agi_net_runtime_selftest() == 0
    }
}
""", files)
        _write(root / "ios/include/agilang_net_runtime.h", r"""
#ifndef AGILANG_NET_RUNTIME_H
#define AGILANG_NET_RUNTIME_H

const char *agi_net_runtime_version(void);
const char *agi_net_runtime_capabilities(void);
int agi_net_runtime_selftest(void);
int agi_ws_broadcast(const char *message);

#endif
""", files)
        _write(root / "ios/AgilangRuntime.podspec", r"""
Pod::Spec.new do |s|
  s.name = 'AgilangRuntime'
  s.version = '1.7.0'
  s.summary = 'AGILANG native C networking runtime bridge for iOS.'
  s.homepage = 'https://example.invalid/agilang'
  s.license = { :type => 'Proprietary' }
  s.author = { 'AGILANG Project' => 'dev@example.invalid' }
  s.platform = :ios, '13.0'
  s.source = { :path => '.' }
  s.source_files = 'AgilangRuntimeBridge.swift', 'include/*.h'
  s.vendored_libraries = 'lib/libagilang_net_runtime.a'
end
""", files)
        _write(root / "ios/README.md", r"""
# iOS AGILANG Runtime Bridge

Use this folder as a CocoaPods/Swift bridge around `libagilang_net_runtime.a`.

Build requirements:

- macOS
- Xcode command-line tools
- `xcrun` / `clang`
- CocoaPods if using the podspec

Expected artifacts:

- `ios/lib/libagilang_net_runtime.a` for device/simulator builds
- Optional `.xcframework` generated by the release workflow
""", files)

    native_dir = Path(__file__).resolve().parent / "native"
    _write(root / "native/agilang_net_runtime.c", (native_dir / "agilang_net_runtime.c").read_text(encoding="utf-8"), files)
    _write(root / "native/agilang_net_runtime.h", (native_dir / "agilang_net_runtime.h").read_text(encoding="utf-8"), files)
    _write(root / "src/agilangNativeRuntime.ts", r"""
import { NativeModules, Platform } from 'react-native';

export type AgilangNativeRuntimeStatus = {
  platform: string;
  available: boolean;
  version?: string;
  capabilities?: any;
};

export function agilangNativeRuntimeStatus(): AgilangNativeRuntimeStatus {
  const mod = NativeModules.AgilangRuntimeModule;
  if (!mod) return { platform: Platform.OS, available: false };
  try {
    const version = mod.nativeVersion?.();
    const raw = mod.nativeCapabilities?.() || '{}';
    return { platform: Platform.OS, available: true, version, capabilities: JSON.parse(raw) };
  } catch (error) {
    return { platform: Platform.OS, available: false };
  }
}
""", files)
    return MobileBridgeResult(root=root, target=target, files=files)


__all__ = [
    "MOBILE_NATIVE_TARGETS",
    "MOBILE_RUNTIME_VERSION",
    "mobile_runtime_matrix",
    "mobile_runtime_capabilities",
    "mobile_runtime_doctor",
    "create_mobile_native_bridge",
    "MobileBridgeResult",
]
