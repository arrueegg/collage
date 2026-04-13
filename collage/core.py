"""Core collage-generation logic, decoupled from the CLI."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image

from .exif import sort_key_exif_then_name, sort_key_name
from .image import FillMode, open_and_orient, render_cell
from .layout import grid_positions
from .utils import collect_images, SUPPORTED_EXTENSIONS, HEIC_SUPPORTED

JPEG_QUALITY = 95


@dataclass
class CollageConfig:
    """All parameters needed to produce a set of collages."""

    input_dir: Path
    output_dir: Path

    # Grid layout
    cols: int = 2
    rows: int = 2

    # Canvas / cell geometry (pixels)
    canvas_w: int = 4800
    canvas_h: int = 7227
    cell_w: int = 2400
    cell_h: int = 3613
    gap: int = 0
    border: int = 0

    # Rendering
    fill_mode: FillMode = "fit"
    bg_color: tuple[int, int, int] = field(default_factory=lambda: (255, 255, 255))

    # Sorting & scanning
    sort: str = "exif"
    recursive: bool = False
    include_leftovers: bool = False

    @property
    def batch_size(self) -> int:
        """Number of images per collage."""
        return self.cols * self.rows


def run(config: CollageConfig) -> list[Path]:
    """
    Discover, sort, batch, and render collages according to *config*.

    Prints progress to stdout, writes JPEG files to config.output_dir,
    and returns the list of paths that were written.
    """
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # ── Discover images ───────────────────────────────────────────────────────
    print(f"Scanning {'recursively ' if config.recursive else ''}for images in: {config.input_dir}")
    images = collect_images(config.input_dir, recursive=config.recursive)

    if not images:
        print("No supported images found. Exiting.")
        return []

    exts     = ", ".join(sorted(SUPPORTED_EXTENSIONS))
    heic_note = " | HEIC: enabled" if HEIC_SUPPORTED else ""
    print(f"Found {len(images)} image(s). Formats: {exts}{heic_note}")

    # ── Sort ──────────────────────────────────────────────────────────────────
    key_fn = sort_key_exif_then_name if config.sort == "exif" else sort_key_name
    label  = "EXIF capture time → filename" if config.sort == "exif" else "filename"
    print(f"Sorting by: {label}")
    images.sort(key=key_fn)

    # ── Layout summary ────────────────────────────────────────────────────────
    print(
        f"Layout: {config.cols}×{config.rows}  |  "
        f"Canvas: {config.canvas_w}×{config.canvas_h}px  |  "
        f"Cell: {config.cell_w}×{config.cell_h}px  |  "
        f"Gap: {config.gap}px  |  Border: {config.border}px  |  "
        f"Fill mode: {config.fill_mode}"
    )

    # ── Batch into groups ─────────────────────────────────────────────────────
    bs           = config.batch_size
    full_batches = len(images) // bs
    remainder    = len(images) % bs

    if remainder:
        if config.include_leftovers:
            print(f"  {remainder} leftover image(s) → final collage with blank cells.")
        else:
            print(
                f"  {remainder} image(s) skipped (not enough for a full batch of {bs}). "
                "Use --include-leftovers to include them."
            )

    batches: list[list[Path]] = [images[i * bs: i * bs + bs] for i in range(full_batches)]
    if remainder and config.include_leftovers:
        batches.append(images[full_batches * bs:])

    if not batches:
        print(f"Not enough images to form even one collage (need {bs}). Exiting.")
        return []

    print(f"\nGenerating {len(batches)} collage(s) → {config.output_dir}\n")

    # ── Render ────────────────────────────────────────────────────────────────
    positions   = grid_positions(config.border, config.cell_w, config.cell_h,
                                 config.gap, config.cols, config.rows)
    pad_w       = len(str(len(batches)))
    output_paths: list[Path] = []

    for idx, batch in enumerate(batches, start=1):
        padded: list[Optional[Path]] = list(batch) + [None] * (bs - len(batch))
        out_path = config.output_dir / f"collage_{idx:03d}.jpg"

        print(f"  [{idx:{pad_w}}/{len(batches)}] {out_path.name}")
        for p in batch:
            rel = p.relative_to(config.input_dir) if p.is_relative_to(config.input_dir) else p.name
            print(f"         {rel}")

        canvas = Image.new("RGB", (config.canvas_w, config.canvas_h), config.bg_color)

        for path, (x, y) in zip(padded, positions):
            if path is None:
                cell = Image.new("RGB", (config.cell_w, config.cell_h), config.bg_color)
            else:
                try:
                    img = open_and_orient(path)
                except Exception as exc:
                    print(f"    WARNING: could not open {path.name}: {exc}", file=sys.stderr)
                    img = Image.new("RGB", (config.cell_w, config.cell_h), (80, 80, 80))

                cell = render_cell(img, config.cell_w, config.cell_h,
                                   config.fill_mode, config.bg_color)

            canvas.paste(cell, (x, y))

        canvas.save(out_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
        output_paths.append(out_path)

    print(f"\nDone. {len(batches)} collage(s) saved to: {config.output_dir.resolve()}")
    return output_paths
