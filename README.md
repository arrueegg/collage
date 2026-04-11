# make_collages

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Pillow](https://img.shields.io/badge/Pillow-10%2B-green)
![HEIC](https://img.shields.io/badge/HEIC%2FHEIF-supported-orange)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

A command-line tool that turns a folder of photos into 2×2 grid collages. Sorts images chronologically by EXIF capture time, groups them in batches of four, and outputs one high-quality JPEG per batch.

Built for iPhone photo libraries — handles HEIC/HEIF natively, applies EXIF orientation automatically, and auto-rotates images to best fill each cell.

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

**12 images → 3 collages. 20 images → 5 collages.**
Leftover images (fewer than 4) are skipped by default, with a message.

---

## Layout anatomy

```
◄──────────────── canvas_w ─────────────────►

▲  ┌──────────────────────────────────────┐
│  │           border                     │
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
│  │           border                     │
▼  └──────────────────────────────────────┘

  cell_w = (canvas_w − 2×border − gap) / 2
  cell_h = (canvas_h − 2×border − gap) / 2
```

Default: `--gap 0 --border 0` → images are perfectly flush, no background visible.

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
make_collages.py      ← thin entry point (run without installing)
pyproject.toml        ← package config  (installs make-collages command)
requirements.txt      ← dependency list
collage/
├── __init__.py
├── cli.py            argument parsing and entry point
├── core.py           CollageConfig dataclass + run() orchestration
├── exif.py           EXIF reading and sort keys
├── image.py          loading, orientation, fit/cover renderers
├── layout.py         canvas/cell geometry helpers
└── utils.py          file discovery, parse_ratio, parse_color
```

---

## Installation

```bash
git clone https://github.com/yourname/make_collages.git
cd make_collages

python3 -m venv env
source env/bin/activate       # Windows: env\Scripts\activate

pip install -e ".[heic]"      # registers the make-collages command
```

**Without installing** (run the script directly):
```bash
pip install -r requirements.txt
python make_collages.py --input ./photos --output ./collages
```

---

## Quick start

```bash
make-collages --input ./photos --output ./collages
```

Produces portrait `8.9:13.4` collages at 4800 px wide, flush images, white background.

---

## All options

```
make-collages --input DIR --output DIR [options]
```

### Input / output

| Flag | Description |
|---|---|
| `--input` / `-i` | Source folder *(required)* |
| `--output` / `-o` | Output folder for JPEG collages *(required)* |

### Size

Use `--ratio` + `--pixels-wide` **or** `--cell-width` + `--cell-height` — not both.

| Flag | Default | Description |
|---|---|---|
| `--ratio W:H` | `8.9:13.4` | Output aspect ratio. Decimals accepted: `16:9`, `4:3`, `8.9:13.4` |
| `--pixels-wide PX` | `4800` | Total canvas width in pixels. Height derived from ratio |
| `--cell-width PX` | — | Override: each cell's width in pixels |
| `--cell-height PX` | — | Override: each cell's height in pixels |

### Layout

| Flag | Default | Description |
|---|---|---|
| `--gap PX` | `0` | Space between columns and between rows |
| `--border PX` | `0` | Outer border around the collage |
| `--fill-mode` | `fit` | `fit` — full image, bars on one side. `cover` — crop edges, no bars |
| `--bg-color COLOR` | `ffffff` | Hex (`1a1a1a`) or `r,g,b` (`26,26,26`) |

### Sorting & scanning

| Flag | Default | Description |
|---|---|---|
| `--sort` | `exif` | `exif` — EXIF capture time → filename. `name` — filename only |
| `--recursive` / `-r` | off | Scan subfolders recursively |
| `--include-leftovers` | off | Create a final collage even if fewer than 4 images remain |

---

## Examples

**Default — portrait, white background, flush:**
```bash
make-collages --input ./photos --output ./collages
```

**4K landscape, cover mode:**
```bash
make-collages --input ./photos --output ./collages \
  --ratio 16:9 --pixels-wide 3840 --fill-mode cover
```

**Square with gap and dark background:**
```bash
make-collages --input ./photos --output ./collages \
  --ratio 1:1 --gap 8 --border 16 --bg-color 1a1a1a
```

**Recursive scan, include leftovers:**
```bash
make-collages --input ./photos --output ./collages \
  --recursive --include-leftovers
```

---

## Using as a library

```python
from pathlib import Path
from collage.core import CollageConfig, run
from collage.layout import cell_size_from_canvas, canvas_size_from_ratio

canvas_w, canvas_h = canvas_size_from_ratio(8.9, 13.4, pixels_wide=4800)
cell_w, cell_h     = cell_size_from_canvas(canvas_w, canvas_h, gap=0, border=0)

config = CollageConfig(
    input_dir=Path("./photos"),
    output_dir=Path("./collages"),
    canvas_w=canvas_w, canvas_h=canvas_h,
    cell_w=cell_w,     cell_h=cell_h,
    gap=0, border=0,
    fill_mode="fit",
    bg_color=(255, 255, 255),
    sort="exif",
    recursive=False,
    include_leftovers=False,
)

run(config)
```

---

## Supported formats

| Format | Requirement |
|---|---|
| JPG / JPEG | Always supported |
| PNG | Always supported |
| HEIC / HEIF | `pillow-heif` (included in `requirements.txt`) |
