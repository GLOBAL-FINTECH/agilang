"""Native image operations for AGILANG AIFlow datasets."""
from __future__ import annotations

from typing import Any, Sequence


def pixel_scale(value: Any, scale: float = 255.0) -> Any:
    if isinstance(value, list):
        return [pixel_scale(v, scale) for v in value]
    return float(value) / scale


def flip_left_right(image: Sequence[Sequence[Any]]) -> list[list[Any]]:
    return [list(reversed(row)) for row in image]


def flip_top_bottom(image: Sequence[Sequence[Any]]) -> list[list[Any]]:
    return [list(row) for row in reversed(image)]


def crop_center(image: Sequence[Sequence[Any]], rows: int, cols: int) -> list[list[Any]]:
    h = len(image)
    w = len(image[0]) if h else 0
    if rows > h or cols > w:
        raise ValueError("requested crop is larger than input")
    r0 = (h - rows) // 2
    c0 = (w - cols) // 2
    return [list(row[c0:c0 + cols]) for row in image[r0:r0 + rows]]


def resize_nearest(image: Sequence[Sequence[Any]], rows: int, cols: int) -> list[list[Any]]:
    h = len(image)
    w = len(image[0]) if h else 0
    if h == 0 or w == 0:
        return []
    if rows <= 0 or cols <= 0:
        raise ValueError("output shape must be positive")
    out = []
    for r in range(rows):
        src_r = min(h - 1, int(r * h / rows))
        out_row = []
        for c in range(cols):
            src_c = min(w - 1, int(c * w / cols))
            out_row.append(image[src_r][src_c])
        out.append(out_row)
    return out


__all__ = ["pixel_scale", "flip_left_right", "flip_top_bottom", "crop_center", "resize_nearest"]
