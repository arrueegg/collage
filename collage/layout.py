"""Canvas geometry — deriving cell sizes and grid positions for any NxM layout."""

from __future__ import annotations


def cell_size_from_canvas(
    canvas_w: int,
    canvas_h: int,
    gap: int,
    border: int,
    cols: int = 2,
    rows: int = 2,
) -> tuple[int, int]:
    """
    Derive cell dimensions from a desired total canvas size.

    Layout (gap separates each column/row pair):
        canvas_w = 2*border + cols*cell_w + (cols-1)*gap
        canvas_h = 2*border + rows*cell_h + (rows-1)*gap
    """
    cell_w = (canvas_w - 2 * border - (cols - 1) * gap) // cols
    cell_h = (canvas_h - 2 * border - (rows - 1) * gap) // rows
    if cell_w <= 0 or cell_h <= 0:
        raise ValueError(
            f"Border ({border}px) + gap ({gap}px) leave no room for cells "
            f"inside a {canvas_w}×{canvas_h} canvas with a {cols}×{rows} grid."
        )
    return cell_w, cell_h


def canvas_size_from_cells(
    cell_w: int,
    cell_h: int,
    gap: int,
    border: int,
    cols: int = 2,
    rows: int = 2,
) -> tuple[int, int]:
    """Inverse of cell_size_from_canvas — derive canvas size from cell dimensions."""
    return (
        2 * border + cols * cell_w + (cols - 1) * gap,
        2 * border + rows * cell_h + (rows - 1) * gap,
    )


def canvas_size_from_ratio(
    ratio_w: float,
    ratio_h: float,
    pixels_wide: int,
) -> tuple[int, int]:
    """Derive canvas pixel dimensions from an aspect ratio and a pixel width."""
    return pixels_wide, round(pixels_wide * ratio_h / ratio_w)


def grid_positions(
    border: int,
    cell_w: int,
    cell_h: int,
    gap: int,
    cols: int = 2,
    rows: int = 2,
) -> list[tuple[int, int]]:
    """
    Return (x, y) paste positions for every cell in a cols×rows grid,
    ordered left-to-right, top-to-bottom.
    """
    return [
        (border + c * (cell_w + gap), border + r * (cell_h + gap))
        for r in range(rows)
        for c in range(cols)
    ]
