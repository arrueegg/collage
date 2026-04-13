# make_collages

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Pillow](https://img.shields.io/badge/Pillow-10%2B-green)
![HEIC](https://img.shields.io/badge/HEIC%2FHEIF-supported-orange)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

A tool that turns a folder of photos into grid collages. Sorts images chronologically by EXIF capture time, groups them in batches, and outputs one high-quality JPEG per batch.

Available as a **browser UI** (no terminal knowledge needed) or a **CLI** for scripting.
Built for iPhone photo libraries — handles HEIC/HEIF natively, applies EXIF orientation automatically, and auto-rotates images to best fill each cell.

---

## Quick start

```bash
git clone https://github.com/yourname/make_collages.git
cd make_collages
```

**Mac — double-click to launch:**
> Double-click `launch.command` in Finder.
> On first run it sets up the environment and installs dependencies automatically, then opens the UI in your browser.

**Any platform — terminal:**
```bash
make install   # create venv + install deps (once)
make ui        # open browser UI
```

---

## How it works

```
Input folder                    Output folder
────────────────                ──────────────────────────────────────
photo_001.heic  ─┐
photo_002.heic  ─┤  collage     collage_001.jpg   collage_002.jpg
photo_003.heic  ─┤  ───────►   ┌───────┬───────┐  ┌───────┬───────┐
photo_004.heic  ─┘             │  001  │  002  │  │  005  │  006  │
                               ├───────┼───────┤  ├───────┼───────┤
photo_005.heic  ─┐             │  003  │  004  │  │  007  │  008  │
photo_006.heic  ─┤             └───────┴───────┘  └───────┴───────┘
photo_007.heic  ─┤
photo_008.heic  ─┘
```

The grid is configurable — `2x2` (default), `3x2`, `1x3`, `3x3`, and more.
Leftover images (fewer than one full batch) are skipped by default, with a message.

---

## Layout anatomy

```
◄──────────────── canvas_w ─────────────────►

▲  ┌──────────────────────────────────────┐
│  │              border                  │
│  │   ┌──────────────┬──────────────┐    │
│  │   │              │              │    │
c  │ b │    cell      │ gap  cell    │ b  │
a  │ o │              │              │ o  │
n  │ r ├──────────────┼──────────────┤ r  │
v  │ d │     gap      │              │ d  │
a  │ e │              │              │ e  │
s  │ r │    cell      │    cell      │ r  │
_  │   │              │              │    │
h  │   └──────────────┴──────────────┘    │
│  │              border                  │
▼  └──────────────────────────────────────┘

  cell_w = (canvas_w − 2×border − (cols−1)×gap) / cols
  cell_h = (canvas_h − 2×border − (rows−1)×gap) / rows
```

Default: `gap 0`, `border 0` → images are perfectly flush, no background visible.

---

## fill-mode: fit vs cover

```
Original image        fit (default)         cover
┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│                │    │▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒│    │                │
│                │    │                │    │                │
│   4 : 3        │ →  │    4 : 3       │ →  │   (cropped)    │
│                │    │                │    │                │
│                │    │▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒│    │                │
└────────────────┘    └────────────────┘    └────────────────┘
                        ▒ = bg-color          no bars, edges
                        full image visible    slightly cropped
```

---

## Features

- Configurable grid layout: `2x2`, `3x2`, `1x3`, `3x3`, and any other combination
- Sorts by EXIF capture time (`DateTimeOriginal`) — falls back to filename
- HEIC/HEIF support via `pillow-heif`
- Specify output size as an **aspect ratio** (`8.9:13.4`, `16:9`, `1:1`) — no pixel maths needed
- Auto-rotates images to match cell orientation, minimising wasted space
- `fit` mode: full image always visible, bars on **one axis only**
- `cover` mode: centre-crops to fill cell completely, no bars
- Configurable gap, border, and background colour
- Recursive folder scan and leftover-image handling

---

## Project structure

```
launch.command        ← double-click in Finder to launch UI (Mac)
Makefile              ← make install / make ui / make run
app.py                ← Gradio browser UI
make_collages.py      ← thin CLI entry point (run without installing)
pyproject.toml        ← package config
requirements.txt      ← dependency list
collage/
├── __init__.py
├── cli.py            argument parsing and entry point
├── core.py           CollageConfig dataclass + run() orchestration
├── exif.py           EXIF reading and sort keys
├── image.py          loading, orientation, fit/cover renderers
├── layout.py         canvas/cell geometry helpers
└── utils.py          file discovery, parse_ratio, parse_layout, parse_color
```

---

## Installation

**Option A — double-click (Mac):**
Double-click `launch.command`. Everything is handled automatically on first run.

**Option B — terminal:**
```bash
make install
# or manually:
python3 -m venv env
source env/bin/activate
pip install -e ".[heic,ui]"
```

---

## Launching the UI

```bash
# Mac: double-click launch.command in Finder
# or:
make ui
# or:
python app.py
```

Opens at `http://localhost:7860`. The UI has three option panels:

| Panel | Controls |
|---|---|
| Grid & size | Layout (cols×rows), aspect ratio, canvas width |
| Style | Fill mode, gap, border, background colour |
| Sorting & extras | Sort by EXIF/name, recursive scan, include leftovers |

---

## CLI usage

For scripting or automation, use the `make-collages` command directly:

```bash
# Basic
make-collages --input ./photos --output ./collages

# Custom grid and ratio
make-collages --input ./photos --output ./collages --layout 3x2 --ratio 16:9

# Cover mode, dark background
make-collages --input ./photos --output ./collages --fill-mode cover --bg-color 1a1a1a
```

### All CLI options

#### Input / output

| Flag | Description |
|---|---|
| `--input` / `-i` | Source folder *(required)* |
| `--output` / `-o` | Output folder for JPEG collages *(required)* |

#### Grid

| Flag | Default | Description |
|---|---|---|
| `--layout COLSxROWS` | `2x2` | Grid size: `2x2` = 4 per collage, `3x2` = 6, `1x3` = 3, etc. |

#### Size

Use `--ratio` + `--pixels-wide` **or** `--cell-width` + `--cell-height` — not both.

| Flag | Default | Description |
|---|---|---|
| `--ratio W:H` | `8.9:13.4` | Output aspect ratio. Decimals accepted |
| `--pixels-wide PX` | `4800` | Total canvas width. Height derived from ratio |
| `--cell-width PX` | — | Override: each cell's width in pixels |
| `--cell-height PX` | — | Override: each cell's height in pixels |

#### Layout

| Flag | Default | Description |
|---|---|---|
| `--gap PX` | `0` | Space between columns and between rows |
| `--border PX` | `0` | Outer border around the collage |
| `--fill-mode` | `fit` | `fit` — full image, bars on one side. `cover` — crop edges, no bars |
| `--bg-color COLOR` | `ffffff` | Hex (`1a1a1a`) or `r,g,b` |

#### Sorting & scanning

| Flag | Default | Description |
|---|---|---|
| `--sort` | `exif` | `exif` — EXIF capture time → filename. `name` — filename only |
| `--recursive` / `-r` | off | Scan subfolders recursively |
| `--include-leftovers` | off | Create a final collage even if fewer than one full batch remains |

---

## How sorting works

1. **`--sort exif` (default)** — reads `DateTimeOriginal` from EXIF metadata. Falls back to `DateTimeDigitized`, then `DateTime`. Images without EXIF dates go last, sorted by filename. iPhone photos always embed `DateTimeOriginal`, so this produces a reliable chronological order.
2. **`--sort name`** — case-insensitive filename sort.

## How image orientation works

Two layers of correction are applied before placing each image:

1. **EXIF orientation tag** — `ImageOps.exif_transpose` rotates pixel data to match the tag (e.g. portrait shots stored as landscape on iPhone).
2. **Cell orientation matching** — if the image and cell orientations still differ, the image is rotated 90° to best fill the cell and minimise whitespace.

---

## Using as a library

```python
from pathlib import Path
from collage.core import CollageConfig, run
from collage.layout import cell_size_from_canvas, canvas_size_from_ratio

canvas_w, canvas_h = canvas_size_from_ratio(8.9, 13.4, pixels_wide=4800)
cell_w, cell_h     = cell_size_from_canvas(canvas_w, canvas_h, gap=0, border=0, cols=2, rows=2)

config = CollageConfig(
    input_dir=Path("./photos"),
    output_dir=Path("./collages"),
    cols=2, rows=2,
    canvas_w=canvas_w, canvas_h=canvas_h,
    cell_w=cell_w,     cell_h=cell_h,
    gap=0, border=0,
    fill_mode="fit",
    bg_color=(255, 255, 255),
    sort="exif",
    recursive=False,
    include_leftovers=False,
)

output_paths = run(config)
```

---

## Supported formats

| Format | Requirement |
|---|---|
| JPG / JPEG | Always supported |
| PNG | Always supported |
| HEIC / HEIF | `pillow-heif` (included in `requirements.txt`) |
