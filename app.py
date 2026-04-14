"""
Gradio visual interface for make_collages.

Launch with:
    python app.py
    # or, after pip install -e .[ui]:
    make-collages-ui

Then open http://localhost:7860 in your browser.
"""

from __future__ import annotations

import contextlib
import io
import socket
from pathlib import Path

import gradio as gr

from collage.core import CollageConfig, run
from collage.layout import cell_size_from_canvas, canvas_size_from_ratio
from collage.utils import HEIC_SUPPORTED, SUPPORTED_EXTENSIONS, parse_color, parse_layout, parse_ratio

# ── Layout choices shown in the dropdown ─────────────────────────────────────
LAYOUT_OPTIONS = ["1x1", "1x2", "2x1", "2x2", "2x3", "3x2", "3x3", "4x2", "2x4", "4x3", "3x4"]

PREVIEW_LIMIT = 12   # max collages shown in the gallery
HOME_DIR = Path.home()


def find_free_port(start: int = 7860, stop: int = 7999) -> int:
    for port in range(start, stop + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise OSError(f"No free local port found in range {start}-{stop}.")


# ── UI helpers ────────────────────────────────────────────────────────────────

def _folder_from_selection(selection: str | list[str] | None) -> str:
    """Return a usable folder path from a FileExplorer selection."""
    if isinstance(selection, list):
        selection = selection[0] if selection else None
    if not selection:
        return ""

    path = Path(selection).expanduser()
    if path.is_file():
        path = path.parent
    return str(path)


def _suggest_output_folder(input_folder: str) -> str:
    path = Path(input_folder).expanduser()
    if not input_folder or not path.exists():
        return ""
    if path.is_file():
        path = path.parent
    return str(path.parent / f"{path.name}_collages")


def choose_input_folder(
    selection: str | list[str] | None,
    current_output: str,
    recursive: bool,
) -> tuple[str, str, str]:
    input_folder = _folder_from_selection(selection)
    output_folder = current_output.strip() or _suggest_output_folder(input_folder)
    status = scan_folder(input_folder, recursive)
    return input_folder, output_folder, status


def choose_output_folder(selection: str | list[str] | None) -> str:
    return _folder_from_selection(selection)


def scan_folder(input_folder: str, recursive: bool) -> str:
    if not input_folder.strip():
        return "Choose an input folder to scan."

    input_dir = Path(input_folder).expanduser()
    if not input_dir.is_dir():
        return f"'{input_folder}' is not a valid folder."

    glob_fn = input_dir.rglob if recursive else input_dir.glob
    images = [
        path for path in glob_fn("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    formats = ", ".join(sorted({path.suffix.lower() for path in images})) or "none"
    return f"{len(images)} supported image(s) found. Formats: {formats}."


# ── Core generate function ────────────────────────────────────────────────────

def generate(
    input_folder: str,
    output_folder: str,
    layout_str: str,
    ratio_str: str,
    pixels_wide: int,
    fill_mode: str,
    gap: int,
    border: int,
    bg_hex: str,
    sort_mode: str,
    recursive: bool,
    include_leftovers: bool,
) -> tuple[str, list[str]]:
    """
    Run the collage generator and return (log_text, list_of_image_paths).
    Called by the Gradio interface when the user clicks Generate.
    """
    log = io.StringIO()

    try:
        # ── Validate inputs ───────────────────────────────────────────────────
        input_dir = Path(input_folder.strip()) if input_folder.strip() else None
        if not input_dir or not input_dir.is_dir():
            return f"Error: '{input_folder}' is not a valid folder.", []

        output_dir = Path(output_folder.strip()) if output_folder.strip() else None
        if not output_dir:
            return "Error: please specify an output folder.", []

        try:
            cols, rows = parse_layout(layout_str)
        except Exception as exc:
            return f"Error: {exc}", []

        try:
            ratio_w, ratio_h = parse_ratio(ratio_str)
        except Exception as exc:
            return f"Error: {exc}", []

        try:
            bg_color = parse_color(bg_hex.lstrip("#"))
        except Exception as exc:
            return f"Error: {exc}", []

        # ── Compute geometry ──────────────────────────────────────────────────
        canvas_w, canvas_h = canvas_size_from_ratio(ratio_w, ratio_h, pixels_wide)
        try:
            cell_w, cell_h = cell_size_from_canvas(canvas_w, canvas_h, gap, border, cols, rows)
        except ValueError as exc:
            return f"Error: {exc}", []

        config = CollageConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            cols=cols,
            rows=rows,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
            cell_w=cell_w,
            cell_h=cell_h,
            gap=gap,
            border=border,
            fill_mode=fill_mode,
            bg_color=bg_color,
            sort=sort_mode,
            recursive=recursive,
            include_leftovers=include_leftovers,
        )

        # ── Run (capture stdout into log) ─────────────────────────────────────
        with contextlib.redirect_stdout(log):
            output_paths = run(config)

    except Exception as exc:
        return f"Unexpected error: {exc}", []

    log_text    = log.getvalue()
    image_paths = [str(p) for p in output_paths[:PREVIEW_LIMIT]]

    if len(output_paths) > PREVIEW_LIMIT:
        log_text += f"\n(Showing first {PREVIEW_LIMIT} of {len(output_paths)} collages in preview.)"

    return log_text, image_paths


# ── UI definition ─────────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    heic_note = "HEIC/HEIF supported" if HEIC_SUPPORTED else "HEIC/HEIF not available (install pillow-heif)"

    with gr.Blocks(title="make_collages") as demo:

        gr.Markdown("# make_collages\nGenerate photo collages from a folder of images.")
        gr.Markdown(f"*{heic_note}*")

        # ── Folders ───────────────────────────────────────────────────────────
        with gr.Row(equal_height=True):
            with gr.Column(scale=2, min_width=360):
                input_folder = gr.Textbox(
                    label="Input folder",
                    placeholder="/path/to/photos",
                    scale=3,
                )
                with gr.Accordion("Browse input folder", open=True):
                    input_browser = gr.FileExplorer(
                        glob="**/*",
                        ignore_glob="*/.*",
                        file_count="single",
                        root_dir=HOME_DIR,
                        label="Home",
                        height=260,
                    )

            with gr.Column(scale=2, min_width=360):
                output_folder = gr.Textbox(
                    label="Output folder",
                    placeholder="/path/to/collages",
                    scale=3,
                )
                with gr.Accordion("Browse output folder", open=False):
                    output_browser = gr.FileExplorer(
                        glob="**/*",
                        ignore_glob="*/.*",
                        file_count="single",
                        root_dir=HOME_DIR,
                        label="Home",
                        height=260,
                    )

            with gr.Column(scale=1, min_width=260):
                folder_status = gr.Textbox(label="Input scan", lines=4, interactive=False)
                scan_btn = gr.Button("Scan input")
                suggest_output_btn = gr.Button("Suggest output folder")

        # ── Options ───────────────────────────────────────────────────────────
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Grid & size")
                layout_dd   = gr.Dropdown(LAYOUT_OPTIONS, value="2x2", label="Layout (cols × rows)",
                                          info="2x2 = 4 photos per collage, 3x2 = 6, etc.")
                ratio_box   = gr.Textbox(value="8.9:13.4", label="Aspect ratio (W:H)",
                                         info="e.g. 8.9:13.4, 16:9, 1:1, 9:16")
                pixels_wide = gr.Slider(minimum=800, maximum=9600, step=100, value=4800,
                                        label="Canvas width (px)",
                                        info="Height is derived from the ratio.")

            with gr.Column():
                gr.Markdown("### Style")
                fill_mode = gr.Radio(["fit", "cover"], value="fit", label="Fill mode",
                                     info="fit = full image visible  |  cover = crop to fill cell")
                with gr.Row():
                    gap    = gr.Slider(minimum=0, maximum=200, step=2,  value=0,  label="Gap (px)")
                    border = gr.Slider(minimum=0, maximum=200, step=2,  value=0,  label="Border (px)")
                bg_color = gr.ColorPicker(value="#ffffff", label="Background color")

            with gr.Column():
                gr.Markdown("### Sorting & extras")
                sort_mode          = gr.Radio(["exif", "name"], value="exif", label="Sort by",
                                              info="exif = chronological  |  name = filename")
                recursive          = gr.Checkbox(value=False, label="Scan subfolders recursively")
                include_leftovers  = gr.Checkbox(value=False,
                                                 label="Include leftover images (fill blanks)")

        # ── Action ────────────────────────────────────────────────────────────
        with gr.Row():
            btn = gr.Button("Generate collages", variant="primary", scale=1)

        # ── Output ────────────────────────────────────────────────────────────
        with gr.Row():
            log_box = gr.Textbox(label="Log", lines=12, interactive=False, scale=2)
            gallery = gr.Gallery(
                label=f"Preview (first {PREVIEW_LIMIT})",
                columns=3,
                object_fit="contain",
                height=620,
                scale=3,
            )

        # ── Wire up ───────────────────────────────────────────────────────────
        input_browser.change(
            fn=choose_input_folder,
            inputs=[input_browser, output_folder, recursive],
            outputs=[input_folder, output_folder, folder_status],
        )
        output_browser.change(
            fn=choose_output_folder,
            inputs=output_browser,
            outputs=output_folder,
        )
        scan_btn.click(
            fn=scan_folder,
            inputs=[input_folder, recursive],
            outputs=folder_status,
        )
        suggest_output_btn.click(
            fn=_suggest_output_folder,
            inputs=input_folder,
            outputs=output_folder,
        )
        recursive.change(
            fn=scan_folder,
            inputs=[input_folder, recursive],
            outputs=folder_status,
        )
        btn.click(
            fn=generate,
            inputs=[
                input_folder, output_folder,
                layout_dd, ratio_box, pixels_wide,
                fill_mode, gap, border, bg_color,
                sort_mode, recursive, include_leftovers,
            ],
            outputs=[log_box, gallery],
        )

    return demo


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    demo = build_ui()
    demo.launch(
        inbrowser=True,
        server_name="127.0.0.1",
        server_port=find_free_port(),
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()
