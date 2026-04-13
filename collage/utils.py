"""Shared utilities — file discovery, argument type parsers."""

from __future__ import annotations

import argparse
from pathlib import Path

# Optional HEIC support — registered globally on first import
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png"} | ({".heic", ".heif"} if HEIC_SUPPORTED else set())
)


# ── File discovery ────────────────────────────────────────────────────────────

def collect_images(source: Path, recursive: bool) -> list[Path]:
    """Return all supported image paths under *source*, optionally recursive."""
    glob_fn = source.rglob if recursive else source.glob
    return [
        p for p in glob_fn("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


# ── Argument type parsers (used by argparse and Gradio) ───────────────────────

def parse_ratio(value: str) -> tuple[float, float]:
    """
    Parse an aspect ratio string such as '16:9', '4:3', or '8.9:13.4'.
    Returns (width_part, height_part) as floats.
    """
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            f"Invalid ratio '{value}'. Expected W:H  (e.g. 16:9 or 8.9:13.4)."
        )
    try:
        w, h = float(parts[0]), float(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid ratio '{value}'. Both parts must be numbers."
        )
    if w <= 0 or h <= 0:
        raise argparse.ArgumentTypeError(
            f"Ratio parts must be positive, got '{value}'."
        )
    return w, h


def parse_layout(value: str) -> tuple[int, int]:
    """
    Parse a grid layout string such as '2x2', '3x2', or '1x3'.
    Returns (cols, rows) as ints — width first, matching the WxH convention.

    Examples:
        '2x2' → 4 images per collage (2 columns, 2 rows)
        '3x2' → 6 images per collage (3 columns, 2 rows)
        '1x3' → 3 images per collage (1 column,  3 rows)
    """
    parts = value.lower().strip().split("x")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            f"Invalid layout '{value}'. Expected COLSxROWS  (e.g. 2x2 or 3x2)."
        )
    try:
        cols, rows = int(parts[0]), int(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid layout '{value}'. Both parts must be integers."
        )
    if cols < 1 or rows < 1:
        raise argparse.ArgumentTypeError(
            f"Layout cols and rows must be at least 1, got '{value}'."
        )
    return cols, rows


def parse_color(value: str) -> tuple[int, int, int]:
    """
    Parse a colour from a hex string (#rrggbb / rrggbb) or comma-separated
    RGB values (255,255,255).
    """
    value = value.strip().lstrip("#")
    if "," in value:
        parts = [int(v.strip()) for v in value.split(",")]
        if len(parts) != 3:
            raise argparse.ArgumentTypeError(f"Invalid color: '{value}'.")
        return (parts[0], parts[1], parts[2])
    if len(value) == 6:
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    raise argparse.ArgumentTypeError(
        f"Cannot parse color '{value}'. Use hex (ffffff) or r,g,b (255,255,255)."
    )
