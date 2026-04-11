"""Image loading, orientation correction, and cell rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from PIL import Image, ImageOps

FillMode = Literal["fit", "cover"]


# ── Loading ───────────────────────────────────────────────────────────────────

def open_and_orient(path: Path) -> Image.Image:
    """
    Open an image and apply its EXIF orientation tag so pixel data matches
    what the user sees in a photo viewer. Returns an RGB image.
    """
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


# ── Orientation matching ──────────────────────────────────────────────────────

def rotate_to_match_cell(img: Image.Image, cell_w: int, cell_h: int) -> Image.Image:
    """
    Rotate the image 90° if its orientation (portrait/landscape) differs from
    the cell's, maximising coverage and minimising letterbox space.
    """
    img_is_landscape  = img.width >= img.height
    cell_is_landscape = cell_w   >= cell_h
    if img_is_landscape != cell_is_landscape:
        img = img.rotate(90, expand=True)
    return img


# ── Cell renderers ────────────────────────────────────────────────────────────

def render_cell_fit(
    img: Image.Image,
    cell_w: int,
    cell_h: int,
    bg_color: tuple[int, int, int],
) -> Image.Image:
    """
    Scale the image to fit entirely within the cell, preserving aspect ratio.
    Scales both up and down as needed. Background fills any remaining space
    on one axis only — never bars on all four sides.
    """
    scale = min(cell_w / img.width, cell_h / img.height)
    new_w = round(img.width  * scale)
    new_h = round(img.height * scale)
    img   = img.resize((new_w, new_h), Image.LANCZOS)

    cell = Image.new("RGB", (cell_w, cell_h), bg_color)
    cell.paste(img, ((cell_w - new_w) // 2, (cell_h - new_h) // 2))
    return cell


def render_cell_cover(
    img: Image.Image,
    cell_w: int,
    cell_h: int,
) -> Image.Image:
    """
    Scale and centre-crop the image to fill the cell completely.
    No letterbox bars — edges are cropped equally on each side.
    """
    scale = max(cell_w / img.width, cell_h / img.height)
    new_w = round(img.width  * scale)
    new_h = round(img.height * scale)
    img   = img.resize((new_w, new_h), Image.LANCZOS)

    left = (new_w - cell_w) // 2
    top  = (new_h - cell_h) // 2
    return img.crop((left, top, left + cell_w, top + cell_h))


def render_cell(
    img: Image.Image,
    cell_w: int,
    cell_h: int,
    fill_mode: FillMode,
    bg_color: tuple[int, int, int],
) -> Image.Image:
    """
    Rotate image to best match cell orientation, then apply fill_mode.
    This is the single entry point used by the collage renderer.
    """
    img = rotate_to_match_cell(img, cell_w, cell_h)
    if fill_mode == "cover":
        return render_cell_cover(img, cell_w, cell_h)
    return render_cell_fit(img, cell_w, cell_h, bg_color)
