# AGILANG v1.2 Precompiled Native Runtime

AGILANG v1.2 adds bundled precompiled native runtime artifacts so the C HTTP/WebSocket transport can load without forcing every deployment machine to have `gcc` or `clang` installed.

## Included artifact in this package

This package includes a verified Linux x86_64 build generated from `agilang/native/agilang_net_runtime.c`:

```text
agilang/native/prebuilt/linux-x86_64/libagilang_net_runtime.so
agilang/native/prebuilt/linux-x86_64/libagilang_net_runtime.a
agilang/native/prebuilt/linux-x86_64/agilang_net_runtime.o
agilang/native/prebuilt/linux-x86_64/manifest.json
```

The shared library is the runtime loader target. The `.a` and `.o` files are included for native-linking experiments and CI/debug use.

## Runtime behavior

The native loader now uses this order:

1. Explicit library path supplied by the developer.
2. Installed cached runtime under the AGILANG native runtime cache.
3. Matching bundled prebuilt library for the current platform.
4. Local source compilation using `gcc` or `clang`.

This means Linux x86_64 deployments can load the bundled runtime without a compiler.

## CLI commands

Check bundled artifacts:

```bash
agilang runtime prebuilt-status
```

Install the matching prebuilt runtime into the cache/build directory:

```bash
agilang runtime install-prebuilt
```

Run the full runtime diagnostic:

```bash
agilang runtime doctor
```

Build from source manually if needed:

```bash
agilang runtime build -o build/native
```

## Build prebuilt artifacts for another platform

Use the helper script on the target platform:

```bash
python scripts/build_prebuilt_runtime.py --copy-root-native
```

This writes platform-specific artifacts into:

```text
agilang/native/prebuilt/<platform-tag>/
native/prebuilt/<platform-tag>/
```

Expected platform tags include:

```text
linux-x86_64
macos-x86_64
macos-arm64
windows-x86_64
```

## Release automation

The release workflow now builds prebuilt native runtimes on Linux, macOS and Windows runners, merges them into the package tree, validates loading, and uploads them with the release artifacts.

## Security notes

Prebuilt binaries include SHA-256 hashes in `manifest.json`. In production, only load runtime artifacts distributed through a trusted release channel. Do not replace the shared library with unverified binaries.
