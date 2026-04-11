"""Canvas geometry — deriving cell sizes and grid positions."""

from __future__ import annotations


def cell_size_from_canvas(
    canvas_w: int,
    canvas_h: int,
    gap: int,
    border: int,
) -> tuple[int, int]:
    """
    Derive cell dimensions from a desired total canvas size.

    Layout (one gap separates the two columns and two rows):
        canvas_w = 2*border + cell_w + gap + cell_w
        canvas_h = 2*border + cell_h + gap + cell_h
    """
    cell_w = (canvas_w - 2 * border - gap) // 2
    cell_h = (canvas_h - 2 * border - gap) // 2
    if cell_w <= 0 or cell_h <= 0:
        raise ValueError(
            f"Border ({border}px) + gap ({gap}px) leave no room for cells "
            f"inside a {canvas_w}×{canvas_h} canvas."
        )
    return cell_w, cell_h


def canvas_size_from_cells(
    cell_w: int,
    cell_h: int,
    gap: int,
    border: int,
) -> tuple[int, int]:
    """Inverse of cell_size_from_canvas — derive canvas size from cell dimensions."""
    return (2 * border + 2 * cell_w + gap, 2 * border + 2 * cell_h + gap)


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
) -> list[tuple[int, int]]:
    """Return the four (x, y) paste positions for a 2×2 grid, left-to-right, top-to-bottom."""
    return [
        (border,                border),
        (border + cell_w + gap, border),
        (border,                border + cell_h + gap),
        (border + cell_w + gap, border + cell_h + gap),
    ]
