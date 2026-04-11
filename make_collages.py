#!/usr/bin/env python3
"""
make_collages.py — Generate 2×2 photo collages from a folder of images.

Sorts images by EXIF capture time when available, falls back to filename.
Groups images in batches of 4 and writes one JPEG collage per batch.

Size model
----------
Specify the output aspect ratio with --ratio (e.g. 16:9 or 13.4:8.9) and
control the pixel budget with --pixels-wide.  Height is derived automatically:

    canvas_h = round(pixels_wide * ratio_h / ratio_w)
    cell_w   = (canvas_w - 2*border - gap) / 2
    cell_h   = (canvas_h - 2*border - gap) / 2

Alternatively specify --cell-width / --cell-height directly; the canvas
will be sized to fit those cells plus gap and border.

With the defaults (--gap 0 --border 0) images are perfectly flush — no
background fill visible anywhere.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from PIL import Image, ExifTags, ImageOps

# Optional HEIC support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
if HEIC_SUPPORTED:
    SUPPORTED_EXTENSIONS |= {".heic", ".heif"}

JPEG_QUALITY = 95

FillMode = Literal["fit", "cover"]


# ──────────────────────────────────────────────────────────────────────────────
# EXIF helpers
# ──────────────────────────────────────────────────────────────────────────────

def _exif_tag_id(name: str) -> Optional[int]:
    """Return the numeric EXIF tag ID for a given tag name, or None."""
    for tag_id, tag_name in ExifTags.TAGS.items():
        if tag_name == name:
            return tag_id
    return None


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

    for tag_id in filter(None, [
        _exif_tag_id("DateTimeOriginal"),
        _exif_tag_id("DateTimeDigitized"),
        _exif_tag_id("DateTime"),
    ]):
        raw = exif_data.get(tag_id)
        if raw:
            try:
                return datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue

    return None


def sort_key_exif_then_name(path: Path):
    """Sort key: (capture_datetime or max_datetime, filename)."""
    dt = get_capture_time(path)
    return (dt is None, dt or datetime.max, path.name.lower())


def sort_key_name(path: Path):
    """Sort key: lowercase filename only."""
    return path.name.lower()


# ──────────────────────────────────────────────────────────────────────────────
# Image loading & orientation
# ──────────────────────────────────────────────────────────────────────────────

def open_and_orient(path: Path) -> Image.Image:
    """
    Open an image and apply its EXIF orientation tag so the pixel data
    matches what the user sees in a photo viewer.
    """
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def rotate_to_match_cell(img: Image.Image, cell_w: int, cell_h: int) -> Image.Image:
    """
    Rotate the image 90° if doing so makes its orientation match the cell's,
    maximising the area covered and minimising wasted letterbox space.

    A portrait cell (taller than wide) pairs best with a portrait image, and
    a landscape cell with a landscape image.  When they differ, a 90° rotation
    gives a much tighter fit without any cropping.
    """
    img_is_landscape  = img.width >= img.height
    cell_is_landscape = cell_w   >= cell_h
    if img_is_landscape != cell_is_landscape:
        img = img.rotate(90, expand=True)
    return img


# ──────────────────────────────────────────────────────────────────────────────
# Cell rendering — fit (letterbox) or cover (crop)
# ──────────────────────────────────────────────────────────────────────────────

def render_cell_fit(
    img: Image.Image,
    cell_w: int,
    cell_h: int,
    bg_color: tuple[int, int, int],
) -> Image.Image:
    """
    Scale image to fit entirely within the cell, preserving aspect ratio.
    Scales both up and down as needed — bars appear on one axis only.
    Remaining space is filled with bg_color.
    """
    scale = min(cell_w / img.width, cell_h / img.height)
    new_w = round(img.width * scale)
    new_h = round(img.height * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    cell = Image.new("RGB", (cell_w, cell_h), bg_color)
    offset_x = (cell_w - new_w) // 2
    offset_y = (cell_h - new_h) // 2
    cell.paste(img, (offset_x, offset_y))
    return cell


def render_cell_cover(
    img: Image.Image,
    cell_w: int,
    cell_h: int,
) -> Image.Image:
    """
    Scale and centre-crop the image so it covers the entire cell with no
    letterbox bars — may crop edges.  Aspect ratio is preserved.
    """
    src_w, src_h = img.size
    scale = max(cell_w / src_w, cell_h / src_h)
    new_w = round(src_w * scale)
    new_h = round(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
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
    """Rotate image to best match cell orientation, then fit or cover."""
    img = rotate_to_match_cell(img, cell_w, cell_h)
    if fill_mode == "cover":
        return render_cell_cover(img, cell_w, cell_h)
    return render_cell_fit(img, cell_w, cell_h, bg_color)


# ──────────────────────────────────────────────────────────────────────────────
# Layout helpers
# ──────────────────────────────────────────────────────────────────────────────

def compute_cell_size(
    total_w: int,
    total_h: int,
    gap: int,
    border: int,
) -> tuple[int, int]:
    """
    Derive cell dimensions from the desired total canvas size.

    Canvas layout (one gap between two columns/rows):
        total_w = 2*border + cell_w + gap + cell_w  →  cell_w = (total_w - 2*border - gap) / 2
        total_h = 2*border + cell_h + gap + cell_h  →  cell_h = (total_h - 2*border - gap) / 2
    """
    cell_w = (total_w - 2 * border - gap) // 2
    cell_h = (total_h - 2 * border - gap) // 2
    if cell_w <= 0 or cell_h <= 0:
        raise ValueError(
            f"Border ({border}px) + gap ({gap}px) leave no room for cells "
            f"inside a {total_w}×{total_h} canvas."
        )
    return cell_w, cell_h


def compute_canvas_size(
    cell_w: int,
    cell_h: int,
    gap: int,
    border: int,
) -> tuple[int, int]:
    """Inverse of compute_cell_size — derive canvas from cell dimensions."""
    return (2 * border + 2 * cell_w + gap, 2 * border + 2 * cell_h + gap)


def cell_positions(border: int, cell_w: int, cell_h: int, gap: int) -> list[tuple[int, int]]:
    """Return the four (x, y) paste positions for a 2×2 grid."""
    return [
        (border,                  border),
        (border + cell_w + gap,   border),
        (border,                  border + cell_h + gap),
        (border + cell_w + gap,   border + cell_h + gap),
    ]


# ──────────────────────────────────────────────────────────────────────────────
# File discovery
# ──────────────────────────────────────────────────────────────────────────────

def collect_images(source: Path, recursive: bool) -> list[Path]:
    """Return all supported image paths under *source*, optionally recursive."""
    glob_fn = source.rglob if recursive else source.glob
    return [
        p for p in glob_fn("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Ratio parsing
# ──────────────────────────────────────────────────────────────────────────────

def parse_ratio(value: str) -> tuple[float, float]:
    """
    Parse an aspect ratio string such as '16:9', '4:3', or '13.4:8.9'.
    Returns (width_part, height_part) as floats.
    """
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(
            f"Invalid ratio '{value}'. Expected format: W:H  (e.g. 16:9 or 13.4:8.9)"
        )
    try:
        w, h = float(parts[0]), float(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid ratio '{value}'. Both parts must be numbers."
        )
    if w <= 0 or h <= 0:
        raise argparse.ArgumentTypeError(f"Ratio parts must be positive, got '{value}'.")
    return w, h


# ──────────────────────────────────────────────────────────────────────────────
# Colour parsing
# ──────────────────────────────────────────────────────────────────────────────

def parse_color(value: str) -> tuple[int, int, int]:
    """
    Parse a colour from:
      - CSS hex string: #rrggbb or rrggbb
      - Comma-separated RGB: 255,255,255
    """
    value = value.strip().lstrip("#")
    if "," in value:
        parts = [int(v.strip()) for v in value.split(",")]
        if len(parts) != 3:
            raise argparse.ArgumentTypeError(f"Invalid color: '{value}'")
        return (parts[0], parts[1], parts[2])
    if len(value) == 6:
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    raise argparse.ArgumentTypeError(
        f"Cannot parse color '{value}'. Use hex (#ffffff) or r,g,b (255,255,255)."
    )


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="make_collages",
        description=(
            "Generate 2×2 photo collages from a folder of images.\n\n"
            "Size: set --ratio (e.g. 16:9 or 13.4:8.9) and --pixels-wide.\n"
            "Height is derived automatically from the ratio.\n"
            "Or use --cell-width/--cell-height to control each cell directly.\n\n"
            "By default images are flush with no gaps (--gap 0 --border 0)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # I/O
    io = parser.add_argument_group("input / output")
    io.add_argument("--input",  "-i", required=True, metavar="DIR",
                    help="Source folder containing photos.")
    io.add_argument("--output", "-o", required=True, metavar="DIR",
                    help="Destination folder for collage JPEGs.")

    # Size — ratio-based (primary) or cell-pixel override
    size = parser.add_argument_group(
        "size  (use --ratio/--pixels-wide  OR  --cell-width/--cell-height, not both)"
    )
    size.add_argument(
        "--ratio", type=parse_ratio, default="8.9:13.4", metavar="W:H",
        help="Aspect ratio of the final collage, e.g. 9:16 or 8.9:13.4. [default: 8.9:13.4]",
    )
    size.add_argument(
        "--pixels-wide", type=int, default=4800, metavar="PX",
        help="Total canvas width in pixels; height is derived from --ratio. [default: 4800]",
    )
    size.add_argument("--cell-width",  type=int, default=None, metavar="PX",
                      help="Width of each image cell in pixels (overrides --ratio/--pixels-wide).")
    size.add_argument("--cell-height", type=int, default=None, metavar="PX",
                      help="Height of each image cell in pixels (overrides --ratio/--pixels-wide).")

    # Layout
    layout = parser.add_argument_group("layout")
    layout.add_argument("--gap",    type=int, default=0, metavar="PX",
                        help="Gap between the two columns and between the two rows. [default: 0]")
    layout.add_argument("--border", type=int, default=0, metavar="PX",
                        help="Outer border around the entire collage. [default: 0]")
    layout.add_argument("--fill-mode", choices=["fit", "cover"], default="fit",
                        help=(
                            "'fit'   — scale image to fit cell, preserve full image "
                            "(letterbox with bg-color if needed). "
                            "'cover' — scale+crop to fill cell completely, no letterbox. "
                            "[default: fit]"
                        ))
    layout.add_argument("--bg-color", type=parse_color, default="ffffff", metavar="COLOR",
                        help="Background/fill color for 'fit' mode and border/gap. "
                             "Hex (#rrggbb) or r,g,b. [default: 000000]")

    # Sort / scan
    misc = parser.add_argument_group("sorting & scanning")
    misc.add_argument("--sort", choices=["exif", "name"], default="exif",
                      help="'exif' sorts by EXIF DateTimeOriginal → filename. "
                           "'name' sorts by filename only. [default: exif]")
    misc.add_argument("--recursive", "-r", action="store_true",
                      help="Scan subfolders recursively.")
    misc.add_argument("--include-leftovers", action="store_true",
                      help="If the last batch has <4 images, still create a collage "
                           "with blank cells for the missing slots.")

    return parser


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    input_dir  = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.is_dir():
        parser.error(f"Input path is not a directory: {input_dir}")

    # ── Resolve cell / canvas size ────────────────────────────────────────────
    using_cell_override = args.cell_width is not None or args.cell_height is not None

    if using_cell_override:
        cell_w = args.cell_width  or args.cell_height
        cell_h = args.cell_height or args.cell_width
        canvas_w, canvas_h = compute_canvas_size(cell_w, cell_h, args.gap, args.border)
    else:
        ratio_w, ratio_h = args.ratio
        canvas_w = args.pixels_wide
        canvas_h = round(canvas_w * ratio_h / ratio_w)
        try:
            cell_w, cell_h = compute_cell_size(canvas_w, canvas_h, args.gap, args.border)
        except ValueError as exc:
            parser.error(str(exc))

    fill_mode: FillMode = args.fill_mode
    bg_color: tuple[int, int, int] = args.bg_color

    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Discover & sort images ────────────────────────────────────────────────
    print(f"Scanning {'recursively ' if args.recursive else ''}for images in: {input_dir}")
    all_images = collect_images(input_dir, recursive=args.recursive)

    if not all_images:
        print("No supported images found. Exiting.")
        sys.exit(0)

    exts = ', '.join(sorted(SUPPORTED_EXTENSIONS))
    print(f"Found {len(all_images)} image(s). Formats: {exts}"
          + (" | HEIC: enabled" if HEIC_SUPPORTED else ""))

    key_fn = sort_key_exif_then_name if args.sort == "exif" else sort_key_name
    print(f"Sorting by: {'EXIF capture time → filename' if args.sort == 'exif' else 'filename'}")
    all_images.sort(key=key_fn)

    # ── Print layout summary ──────────────────────────────────────────────────
    print(
        f"Canvas: {canvas_w}×{canvas_h}px  |  "
        f"Cell: {cell_w}×{cell_h}px  |  "
        f"Gap: {args.gap}px  |  Border: {args.border}px  |  "
        f"Fill mode: {fill_mode}"
    )

    # ── Batch into groups of 4 ────────────────────────────────────────────────
    full_batches = len(all_images) // 4
    remainder    = len(all_images) % 4

    if remainder:
        if args.include_leftovers:
            print(f"  {remainder} leftover image(s) → final collage with blank cells.")
        else:
            print(
                f"  {remainder} image(s) skipped (not enough for a full batch of 4). "
                "Use --include-leftovers to include them."
            )

    batches: list[list[Path]] = [all_images[i * 4: i * 4 + 4] for i in range(full_batches)]
    if remainder and args.include_leftovers:
        batches.append(all_images[full_batches * 4:])

    if not batches:
        print("Not enough images to form even one collage. Exiting.")
        sys.exit(0)

    print(f"\nGenerating {len(batches)} collage(s) → {output_dir}\n")

    # ── Render ────────────────────────────────────────────────────────────────
    positions = cell_positions(args.border, cell_w, cell_h, args.gap)
    pad_w = len(str(len(batches)))

    for idx, batch in enumerate(batches, start=1):
        padded: list[Optional[Path]] = list(batch) + [None] * (4 - len(batch))
        out_path = output_dir / f"collage_{idx:03d}.jpg"

        print(f"  [{idx:{pad_w}}/{len(batches)}] {out_path.name}")
        for p in batch:
            rel = p.relative_to(input_dir) if p.is_relative_to(input_dir) else p.name
            print(f"         {rel}")

        canvas = Image.new("RGB", (canvas_w, canvas_h), bg_color)

        for path, (x, y) in zip(padded, positions):
            if path is None:
                cell = Image.new("RGB", (cell_w, cell_h), bg_color)
            else:
                try:
                    img = open_and_orient(path)
                except Exception as exc:
                    print(f"    WARNING: could not open {path.name}: {exc}", file=sys.stderr)
                    img = Image.new("RGB", (cell_w, cell_h), (80, 80, 80))

                cell = render_cell(img, cell_w, cell_h, fill_mode, bg_color)

            canvas.paste(cell, (x, y))

        canvas.save(out_path, "JPEG", quality=JPEG_QUALITY, optimize=True)

    print(f"\nDone. {len(batches)} collage(s) saved to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
