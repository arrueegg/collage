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


# ── Argument type parsers (used by argparse) ──────────────────────────────────

def parse_ratio(value: str) -> tuple[float, float]:
    """
    Parse an aspect ratio string such as '16:9', '4:3', or '8.9:13.4'.
    Returns (width_part, height_part) as floats.

    Raises argparse.ArgumentTypeError on bad input.
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


def parse_color(value: str) -> tuple[int, int, int]:
    """
    Parse a colour from a hex string (#rrggbb / rrggbb) or comma-separated
    RGB values (255,255,255).

    Raises argparse.ArgumentTypeError on bad input.
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
