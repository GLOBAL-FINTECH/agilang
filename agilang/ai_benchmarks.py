"""AIFlow benchmark scaffold for reference kernels."""
from __future__ import annotations

import time
from typing import Any, Callable


def time_call(name: str, fn: Callable[[], Any], repeats: int = 10) -> dict[str, Any]:
    repeats = max(1, int(repeats))
    start = time.perf_counter()
    last = None
    for _ in range(repeats):
        last = fn()
    seconds = time.perf_counter() - start
    return {"name": name, "repeats": repeats, "seconds": seconds, "seconds_per_run": seconds / repeats, "last_type": type(last).__name__}


def benchmark_suite(cases: list[tuple[str, Callable[[], Any]]], repeats: int = 10) -> list[dict[str, Any]]:
    return [time_call(name, fn, repeats=repeats) for name, fn in cases]


def compare_reference(name: str, agilang_fn: Callable[[], Any], baseline_fn: Callable[[], Any] | None = None, repeats: int = 10) -> dict[str, Any]:
    result = {"agilang": time_call(name + ":agilang", agilang_fn, repeats)}
    if baseline_fn is not None:
        result["baseline"] = time_call(name + ":baseline", baseline_fn, repeats)
    return result


__all__ = ["time_call", "benchmark_suite", "compare_reference"]
