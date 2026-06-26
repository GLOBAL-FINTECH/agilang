"""Production-facing image operations for AGILANG AIFlow datasets.

The original module only transformed nested pixel arrays. This version keeps the
array helpers and adds practical image loading/saving through Pillow when it is
installed, JSON-array fallback support, grayscale conversion, bilinear resizing,
normalization and simple augmentation helpers.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Sequence


class ImageOpsError(RuntimeError):
    pass


def pixel_scale(value: Any, scale: float = 255.0) -> Any:
    if isinstance(value, list):
        return [pixel_scale(v, scale) for v in value]
    return float(value) / scale


def image_shape(image: Any) -> list[int]:
    if not isinstance(image, list):
        return []
    if not image:
        return [0]
    if isinstance(image[0], list) and image[0] and isinstance(image[0][0], list):
        return [len(image), len(image[0]), len(image[0][0])]
    if isinstance(image[0], list):
        return [len(image), len(image[0])]
    return [len(image)]


def load_image(path: str | Path, *, mode: str = "L", size: tuple[int, int] | None = None, normalize: bool = False) -> Any:
    """Load an image into nested pixel arrays.

    Supported paths:
    - PNG/JPEG/WebP/etc through Pillow when installed.
    - `.json` files containing already-materialized nested arrays.

    `mode="L"` returns a 2D grayscale image. `mode="RGB"` returns a 3D
    rows/cols/channels image.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(path))
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        return pixel_scale(data) if normalize else data
    try:
        from PIL import Image  # type: ignore
    except Exception as exc:
        raise ImageOpsError("Loading PNG/JPEG/WebP images requires Pillow. Install with: pip install pillow, or provide a JSON pixel array.") from exc
    with Image.open(p) as img:
        img = img.convert(mode)
        if size is not None:
            width, height = int(size[0]), int(size[1])
            img = img.resize((width, height))
        pixels = list(img.getdata())
        width, height = img.size
        if mode == "L":
            rows = [[float(pixels[r * width + c]) for c in range(width)] for r in range(height)]
        else:
            rows = [[list(map(float, pixels[r * width + c])) for c in range(width)] for r in range(height)]
        return pixel_scale(rows) if normalize else rows


def save_image(path: str | Path, image: Any, *, mode: str | None = None, scale: float = 255.0) -> str:
    """Save nested pixel arrays as JSON or image files.

    Non-JSON image formats require Pillow. Normalized values in [0, 1] are scaled
    automatically when `scale=255`.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix.lower() == ".json":
        p.write_text(json.dumps(image, indent=2) + "\n", encoding="utf-8")
        return str(p)
    try:
        from PIL import Image  # type: ignore
    except Exception as exc:
        raise ImageOpsError("Saving PNG/JPEG/WebP images requires Pillow. Install with: pip install pillow, or save as .json.") from exc
    shape = image_shape(image)
    if len(shape) == 2:
        rows, cols = shape
        values = [int(max(0, min(255, round(float(image[r][c]) * scale if float(image[r][c]) <= 1.0 else float(image[r][c]))))) for r in range(rows) for c in range(cols)]
        img = Image.new(mode or "L", (cols, rows))
        img.putdata(values)
    elif len(shape) == 3:
        rows, cols, channels = shape
        if channels < 3:
            raise ValueError("RGB image needs at least 3 channels")
        values = []
        for r in range(rows):
            for c in range(cols):
                pix = image[r][c]
                values.append(tuple(int(max(0, min(255, round(float(pix[i]) * scale if float(pix[i]) <= 1.0 else float(pix[i]))))) for i in range(3)))
        img = Image.new(mode or "RGB", (cols, rows))
        img.putdata(values)
    else:
        raise ValueError(f"unsupported image shape: {shape}")
    img.save(p)
    return str(p)


def flip_left_right(image: Sequence[Sequence[Any]]) -> list[list[Any]]:
    return [list(reversed(row)) for row in image]


def flip_top_bottom(image: Sequence[Sequence[Any]]) -> list[list[Any]]:
    return [list(row) for row in reversed(image)]


def rotate90(image: Sequence[Sequence[Any]], clockwise: bool = True) -> list[list[Any]]:
    rows = [list(row) for row in image]
    if not rows:
        return []
    if clockwise:
        return [list(reversed(col)) for col in zip(*rows)]
    return [list(col) for col in reversed(list(zip(*rows)))]


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


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def resize_bilinear(image: Sequence[Sequence[float]], rows: int, cols: int) -> list[list[float]]:
    src = [[float(v) for v in row] for row in image]
    h = len(src)
    w = len(src[0]) if h else 0
    if h == 0 or w == 0:
        return []
    if rows <= 0 or cols <= 0:
        raise ValueError("output shape must be positive")
    if rows == 1 or cols == 1:
        return [[src[min(h - 1, int(r * h / rows))][min(w - 1, int(c * w / cols))] for c in range(cols)] for r in range(rows)]
    out: list[list[float]] = []
    for r in range(rows):
        src_r = r * (h - 1) / (rows - 1)
        r0 = int(math.floor(src_r))
        r1 = min(h - 1, r0 + 1)
        tr = src_r - r0
        row: list[float] = []
        for c in range(cols):
            src_c = c * (w - 1) / (cols - 1)
            c0 = int(math.floor(src_c))
            c1 = min(w - 1, c0 + 1)
            tc = src_c - c0
            top = _lerp(src[r0][c0], src[r0][c1], tc)
            bottom = _lerp(src[r1][c0], src[r1][c1], tc)
            row.append(_lerp(top, bottom, tr))
        out.append(row)
    return out


def rgb_to_grayscale(image: Sequence[Sequence[Sequence[float]]]) -> list[list[float]]:
    out: list[list[float]] = []
    for row in image:
        out_row: list[float] = []
        for pixel in row:
            r = float(pixel[0])
            g = float(pixel[1]) if len(pixel) > 1 else r
            b = float(pixel[2]) if len(pixel) > 2 else r
            out_row.append(0.299 * r + 0.587 * g + 0.114 * b)
        out.append(out_row)
    return out


def normalize_channels(image: Any, *, mean: Sequence[float] | None = None, std: Sequence[float] | None = None, scale: float = 255.0) -> Any:
    mean = list(mean or [])
    std = list(std or [])
    shape = image_shape(image)
    if len(shape) == 2:
        return [[float(v) / scale for v in row] for row in image]
    if len(shape) == 3:
        out = []
        for row in image:
            out_row = []
            for pixel in row:
                values = []
                for i, value in enumerate(pixel):
                    base = float(value) / scale
                    if i < len(mean):
                        base -= float(mean[i])
                    if i < len(std) and float(std[i]) != 0.0:
                        base /= float(std[i])
                    values.append(base)
                out_row.append(values)
            out.append(out_row)
        return out
    return pixel_scale(image, scale=scale)


def image_preprocess(path: str | Path, *, rows: int, cols: int, mode: str = "L", normalize: bool = True, resize: str = "bilinear") -> Any:
    image = load_image(path, mode=mode, normalize=False)
    if mode == "L":
        image = resize_bilinear(image, rows, cols) if resize == "bilinear" else resize_nearest(image, rows, cols)
        return normalize_channels(image) if normalize else image
    # For RGB, Pillow resize is used when loading from non-json if size is provided.
    image = load_image(path, mode=mode, size=(cols, rows), normalize=normalize)
    return image


__all__ = [
    "ImageOpsError",
    "pixel_scale",
    "image_shape",
    "load_image",
    "save_image",
    "flip_left_right",
    "flip_top_bottom",
    "rotate90",
    "crop_center",
    "resize_nearest",
    "resize_bilinear",
    "rgb_to_grayscale",
    "normalize_channels",
    "image_preprocess",
]
