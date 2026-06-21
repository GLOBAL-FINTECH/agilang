# AGILANG v1.1 Runbook

## Check installation

```bash
agilang --version
agilang doctor
agilang test-examples
```

## Build and self-test the native runtime

```bash
agilang runtime doctor
```

Expected result includes:

```json
{
  "available": true,
  "native_selftest": true
}
```

## Use the hybrid runtime in AGILANG

```bash
agilang run examples/native_hybrid_web_runtime.agi
```

## Build C shared runtime manually

Linux:

```bash
gcc -std=c11 -O2 -fPIC -shared native/agilang_net_runtime.c -o build/native/libagilang_net_runtime.so -pthread
```

macOS:

```bash
clang -std=c11 -O2 -fPIC -shared native/agilang_net_runtime.c -o build/native/libagilang_net_runtime.dylib -pthread
```

Windows MinGW:

```powershell
gcc -std=c11 -O2 -shared native\agilang_net_runtime.c -o build\native\agilang_net_runtime.dll -lws2_32
```

## Deployment recommendation

Use Nginx or Caddy for TLS, compression, request buffering, and process supervision. Run AGILANG behind it in Python mode for full framework features, and enable the native C runtime bridge where lower-level transport performance is required.
