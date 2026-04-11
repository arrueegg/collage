"""EXIF metadata helpers — capture-time extraction and sort keys."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image, ExifTags


def _exif_tag_id(name: str) -> Optional[int]:
    """Return the numeric EXIF tag ID for a given tag name, or None."""
    for tag_id, tag_name in ExifTags.TAGS.items():
        if tag_name == name:
            return tag_id
    return None


_DATETIME_TAGS = list(filter(None, [
    _exif_tag_id("DateTimeOriginal"),
    _exif_tag_id("DateTimeDigitized"),
    _exif_tag_id("DateTime"),
]))


def get_capture_time(path: Path) -> Optional[datetime]:
    """
    Extract the capture datetime from EXIF metadata.

    Tries DateTimeOriginal first, then DateTimeDigitized, then DateTime.
    Returns None if no usable EXIF date is found.
    """
    try:
        with Image.open(path) as img:
            exif_data = img._getexif()  # type: ignore[attr-defined]
    except Exception:
        return None

    if not exif_data:
        return None

    for tag_id in _DATETIME_TAGS:
        raw = exif_data.get(tag_id)
        if raw:
            try:
                return datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue

    return None


def sort_key_exif_then_name(path: Path) -> tuple:
    """Sort key: (no-exif flag, capture_datetime, filename) — chronological order."""
    dt = get_capture_time(path)
    return (dt is None, dt or datetime.max, path.name.lower())


def sort_key_name(path: Path) -> str:
    """Sort key: lowercase filename only."""
    return path.name.lower()
