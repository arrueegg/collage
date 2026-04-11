# make_collages

A command-line tool that turns a folder of photos into 2×2 grid collages. Sorts images chronologically by EXIF capture time, groups them in batches of four, and outputs one high-quality JPEG per batch.

Built for iPhone photo libraries — handles HEIC/HEIF natively, applies EXIF orientation automatically, and auto-rotates images to best fill each cell.

## Features

- Sorts by EXIF capture time (falls back to filename)
- HEIC/HEIF support out of the box via `pillow-heif`
- Specify output size as an **aspect ratio** (e.g. `8.9:13.4`, `16:9`) — no pixel maths needed
- Two fill modes: **fit** (full image visible, white bars on one axis if needed) or **cover** (crops edges to fill cell completely)
- Auto-rotates images to match the cell orientation, minimising wasted space
- Configurable gap between cells, outer border, and background colour
- Optional recursive folder scan and handling of leftover images

## Requirements

- Python 3.9+
- [Pillow](https://pillow.readthedocs.io/)
- [pillow-heif](https://github.com/bigcat88/pillow_heif) *(optional — enables HEIC/HEIF)*

## Installation

```bash
# 1. Clone or download this repo
git clone https://github.com/yourname/make_collages.git
cd make_collages

# 2. Create a virtual environment
python3 -m venv env
source env/bin/activate        # Windows: env\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

`requirements.txt`:
```
Pillow>=10.0.0
pillow-heif>=0.13.0
```

## Quick start

```bash
python make_collages.py --input ./photos --output ./collages
```

12 photos → 3 collages. Output is portrait `8.9:13.4` at 4800 px wide, images flush with no gaps, white background.

## Usage

```
python make_collages.py --input DIR --output DIR [options]
```

### Options

#### Input / output

| Flag | Description |
|---|---|
| `--input` / `-i` | Source folder containing photos *(required)* |
| `--output` / `-o` | Destination folder for collage JPEGs *(required)* |

#### Size

Specify size either as a **ratio** (recommended) or directly as **cell pixels** — not both.

| Flag | Default | Description |
|---|---|---|
| `--ratio W:H` | `8.9:13.4` | Aspect ratio of the output collage. Accepts decimals: `16:9`, `4:3`, `8.9:13.4` |
| `--pixels-wide PX` | `4800` | Total canvas width in pixels. Height is derived from `--ratio` |
| `--cell-width PX` | — | Override: set each cell's width directly |
| `--cell-height PX` | — | Override: set each cell's height directly |

#### Layout

| Flag | Default | Description |
|---|---|---|
| `--gap PX` | `0` | Space between the two columns and between the two rows |
| `--border PX` | `0` | Outer border around the entire collage |
| `--fill-mode` | `fit` | `fit` — full image visible, bars on one side if needed. `cover` — crops edges to fill cell completely |
| `--bg-color COLOR` | `ffffff` | Background colour for bars, gap, and border. Hex (`1a1a1a`) or `r,g,b` (`26,26,26`) |

#### Sorting & scanning

| Flag | Default | Description |
|---|---|---|
| `--sort` | `exif` | `exif` — sort by EXIF `DateTimeOriginal` then filename. `name` — filename only |
| `--recursive` / `-r` | off | Scan subfolders recursively |
| `--include-leftovers` | off | If the final batch has fewer than 4 images, still create a collage with blank cells |

## Examples

**Default — portrait collage, white background, flush images:**
```bash
python make_collages.py --input ./photos --output ./collages
```

**16:9 landscape at 4K, cover mode (no bars):**
```bash
python make_collages.py \
  --input ./photos \
  --output ./collages \
  --ratio 16:9 \
  --pixels-wide 3840 \
  --fill-mode cover
```

**Square collage with a thin gap and dark background:**
```bash
python make_collages.py \
  --input ./photos \
  --output ./collages \
  --ratio 1:1 \
  --gap 8 \
  --border 16 \
  --bg-color 1a1a1a
```

**Recursive scan, keep leftover images:**
```bash
python make_collages.py \
  --input ./photos \
  --output ./collages \
  --recursive \
  --include-leftovers
```

## How sorting works

1. **`--sort exif` (default)** — reads `DateTimeOriginal` from EXIF metadata (the moment the shutter fired). Falls back to `DateTimeDigitized`, then `DateTime`. Images with no EXIF date are placed after all dated images, sorted by filename. iPhone photos always embed `DateTimeOriginal`, so this produces a reliable chronological order.

2. **`--sort name`** — case-insensitive filename sort. Useful when files have already been named sequentially.

## How image orientation works

Two layers of orientation correction are applied before an image is placed:

1. **EXIF orientation tag** — `ImageOps.exif_transpose` rotates pixel data to match the tag (e.g. portrait shots stored as landscape on iPhone). The tag is then cleared.
2. **Cell orientation matching** — if the image and cell orientations still differ (one portrait, one landscape), the image is rotated 90° to best fill the cell and minimise whitespace.

## fill-mode: fit vs cover

| | `fit` | `cover` |
|---|---|---|
| Full image visible | Yes | No — edges may be cropped |
| Bars / whitespace | On one axis only if aspect ratios differ | Never |
| Crop | None | Centre-crop — equal amount removed from each side |

## Supported formats

| Format | Notes |
|---|---|
| JPG / JPEG | Always supported |
| PNG | Always supported |
| HEIC / HEIF | Requires `pillow-heif` (installed via `requirements.txt`) |
