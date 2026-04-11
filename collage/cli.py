"""Command-line interface — argument parsing and entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from .core import CollageConfig, run
from .layout import cell_size_from_canvas, canvas_size_from_cells, canvas_size_from_ratio
from .utils import parse_color, parse_ratio


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="make-collages",
        description=(
            "Generate 2×2 photo collages from a folder of images.\n\n"
            "Size: set --ratio (e.g. 9:16 or 8.9:13.4) and --pixels-wide.\n"
            "Height is derived automatically. Or use --cell-width/--cell-height\n"
            "to control each cell directly.\n\n"
            "Images are flush by default (--gap 0 --border 0)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    io = parser.add_argument_group("input / output")
    io.add_argument("--input",  "-i", required=True, metavar="DIR",
                    help="Source folder containing photos.")
    io.add_argument("--output", "-o", required=True, metavar="DIR",
                    help="Destination folder for collage JPEGs.")

    size = parser.add_argument_group(
        "size  (use --ratio/--pixels-wide  OR  --cell-width/--cell-height, not both)"
    )
    size.add_argument(
        "--ratio", type=parse_ratio, default="8.9:13.4", metavar="W:H",
        help="Aspect ratio of the output collage. Accepts decimals. [default: 8.9:13.4]",
    )
    size.add_argument(
        "--pixels-wide", type=int, default=4800, metavar="PX",
        help="Total canvas width in pixels; height derived from --ratio. [default: 4800]",
    )
    size.add_argument("--cell-width",  type=int, default=None, metavar="PX",
                      help="Cell width in pixels (overrides --ratio/--pixels-wide).")
    size.add_argument("--cell-height", type=int, default=None, metavar="PX",
                      help="Cell height in pixels (overrides --ratio/--pixels-wide).")

    layout = parser.add_argument_group("layout")
    layout.add_argument("--gap",    type=int, default=0, metavar="PX",
                        help="Gap between cells (columns and rows). [default: 0]")
    layout.add_argument("--border", type=int, default=0, metavar="PX",
                        help="Outer border around the collage. [default: 0]")
    layout.add_argument(
        "--fill-mode", choices=["fit", "cover"], default="fit",
        help=(
            "'fit'   — full image visible, bars on one side if ratios differ. "
            "'cover' — centre-crop to fill cell, no bars. [default: fit]"
        ),
    )
    layout.add_argument(
        "--bg-color", type=parse_color, default="ffffff", metavar="COLOR",
        help="Background color for bars/gap/border. Hex (ffffff) or r,g,b. [default: ffffff]",
    )

    misc = parser.add_argument_group("sorting & scanning")
    misc.add_argument(
        "--sort", choices=["exif", "name"], default="exif",
        help="'exif' — sort by EXIF capture time then filename. 'name' — filename only. [default: exif]",
    )
    misc.add_argument("--recursive", "-r", action="store_true",
                      help="Scan subfolders recursively.")
    misc.add_argument("--include-leftovers", action="store_true",
                      help="Create a final collage even if fewer than 4 images remain.")

    return parser


def main() -> None:
    """CLI entry point — parse arguments, build config, run."""
    parser = build_parser()
    args   = parser.parse_args()

    input_dir  = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.is_dir():
        parser.error(f"Input path is not a directory: {input_dir}")

    # ── Resolve canvas and cell size ──────────────────────────────────────────
    using_cell_override = args.cell_width is not None or args.cell_height is not None

    if using_cell_override:
        cell_w   = args.cell_width  or args.cell_height
        cell_h   = args.cell_height or args.cell_width
        canvas_w, canvas_h = canvas_size_from_cells(cell_w, cell_h, args.gap, args.border)
    else:
        ratio_w, ratio_h   = args.ratio
        canvas_w, canvas_h = canvas_size_from_ratio(ratio_w, ratio_h, args.pixels_wide)
        try:
            cell_w, cell_h = cell_size_from_canvas(canvas_w, canvas_h, args.gap, args.border)
        except ValueError as exc:
            parser.error(str(exc))

    config = CollageConfig(
        input_dir=input_dir,
        output_dir=output_dir,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        cell_w=cell_w,
        cell_h=cell_h,
        gap=args.gap,
        border=args.border,
        fill_mode=args.fill_mode,
        bg_color=args.bg_color,
        sort=args.sort,
        recursive=args.recursive,
        include_leftovers=args.include_leftovers,
    )

    run(config)


if __name__ == "__main__":
    main()
