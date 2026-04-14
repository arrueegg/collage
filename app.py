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
import html
import io
import socket
import subprocess
from pathlib import Path
from urllib.parse import quote

import gradio as gr

from collage.core import CollageConfig, run
from collage.layout import cell_size_from_canvas, canvas_size_from_ratio
from collage.utils import HEIC_SUPPORTED, SUPPORTED_EXTENSIONS, parse_color, parse_layout, parse_ratio

# ── Layout choices shown in the dropdown ─────────────────────────────────────
LAYOUT_OPTIONS = ["1x1", "1x2", "2x1", "2x2", "2x3", "3x2", "3x3", "4x2", "2x4", "4x3", "3x4"]

PREVIEW_LIMIT = 12   # max collages shown in the gallery
BG_OPTIONS = {
    "White": "ffffff",
    "Soft gray": "f3f4f6",
    "Warm white": "faf7f0",
    "Charcoal": "1f2937",
}

APP_CSS = """
.gradio-container { max-width: 1040px !important; margin: 0 auto !important; }
#app-title { margin: 14px 0 10px; }
#app-title h1 { font-size: 2rem; line-height: 1.05; margin-bottom: 0.2rem; }
#app-title p { color: #626a73; font-size: 0.98rem; margin: 0; }
.folder-chip {
    border: 1px solid #d9e0e7;
    border-radius: 8px;
    padding: 12px 14px;
    background: #fbfcfd;
    min-height: 68px;
}
.folder-chip strong { display: block; color: #20242a; font-size: 0.98rem; margin-bottom: 3px; }
.folder-chip span, .folder-chip a { color: #65707c; font-size: 0.9rem; }
.folder-chip a { text-decoration: none; }
.folder-chip a:hover { text-decoration: underline; }
.status-pill {
    border-radius: 8px;
    padding: 10px 12px;
    background: #f2f7f4;
    border: 1px solid #d7e6dc;
    color: #294837;
    min-height: 48px;
}
button { border-radius: 8px !important; }
textarea, input, select { border-radius: 8px !important; }
#generate-btn { min-height: 44px; max-width: 260px; }
#advanced-paths { opacity: 0.92; }
"""


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

def _escape_applescript(value: str) -> str:
    return value.replace('\\', '\\\\').replace('"', '\\"')


def _ask_directory(prompt: str, current_path: str = "") -> str:
    prompt = _escape_applescript(prompt)
    script = f'POSIX path of (choose folder with prompt "{prompt}")'
    current = Path(current_path).expanduser() if current_path else None
    if current and current.exists():
        if current.is_file():
            current = current.parent
        script = (
            f'POSIX path of (choose folder with prompt "{prompt}" '
            f'default location POSIX file "{_escape_applescript(str(current))}")'
        )

    result = subprocess.run(
        ["/usr/bin/osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _finder_href(path: Path) -> str:
    return "file://" + quote(str(path), safe="/:~")


def _friendly_path(path: Path) -> str:
    try:
        return "~/" + str(path.expanduser().relative_to(Path.home()))
    except ValueError:
        return str(path)


def _folder_chip(path_value: str, empty_title: str, empty_hint: str) -> str:
    if not path_value:
        return f'<div class="folder-chip"><strong>{empty_title}</strong><span>{empty_hint}</span></div>'

    path = Path(path_value).expanduser()
    name = html.escape(path.name or str(path))
    friendly = html.escape(_friendly_path(path))
    if path.exists():
        detail = f'<a href="{_finder_href(path)}" target="_blank">Finder: {friendly}</a>'
    else:
        detail = f'<span>Will be created at {friendly}</span>'
    return f'<div class="folder-chip"><strong>{name}</strong>{detail}</div>'


def _input_chip(path_value: str) -> str:
    return _folder_chip(path_value, "No photo folder selected", "Choose the folder with your images.")


def _output_chip(path_value: str) -> str:
    return _folder_chip(path_value, "No output folder selected", "Use the suggestion or choose where to save collages.")


def _suggest_output_folder(input_folder: str) -> str:
    path = Path(input_folder).expanduser()
    if not input_folder or not path.exists():
        return ""
    if path.is_file():
        path = path.parent
    return str(path.parent / f"{path.name}_collages")


def _background_hex(choice: str) -> str:
    return BG_OPTIONS.get(choice, choice).lstrip("#")


def choose_input_folder(
    current_input: str,
    current_output: str,
    recursive: bool,
) -> tuple[str, str, str, str, str]:
    input_folder = _ask_directory("Choose the folder with your photos", current_input)
    if not input_folder:
        return current_input, current_output, _input_chip(current_input), _output_chip(current_output), scan_folder(current_input, recursive)

    output_folder = current_output.strip() or _suggest_output_folder(input_folder)
    return input_folder, output_folder, _input_chip(input_folder), _output_chip(output_folder), scan_folder(input_folder, recursive)


def choose_output_folder(current_output: str) -> tuple[str, str]:
    output_folder = _ask_directory("Choose where to save collages", current_output)
    if not output_folder:
        return current_output, _output_chip(current_output)
    return output_folder, _output_chip(output_folder)


def update_input_path(input_folder: str, current_output: str, recursive: bool) -> tuple[str, str, str, str, str]:
    input_folder = input_folder.strip()
    output_folder = current_output.strip() or _suggest_output_folder(input_folder)
    return input_folder, output_folder, _input_chip(input_folder), _output_chip(output_folder), scan_folder(input_folder, recursive)


def update_output_path(output_folder: str) -> tuple[str, str]:
    output_folder = output_folder.strip()
    return output_folder, _output_chip(output_folder)


def scan_folder(input_folder: str, recursive: bool) -> str:
    if not input_folder.strip():
        return '<div class="status-pill">Choose an input folder to scan.</div>'

    input_dir = Path(input_folder).expanduser()
    if not input_dir.is_dir():
        return '<div class="status-pill">Selected folder is not available.</div>'

    glob_fn = input_dir.rglob if recursive else input_dir.glob
    images = [
        path for path in glob_fn("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    formats = ", ".join(sorted({path.suffix.lower().lstrip(".").upper() for path in images})) or "none"
    return f'<div class="status-pill"><strong>{len(images)}</strong> supported image(s) found. Formats: {formats}.</div>'


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
    bg_choice: str,
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
            bg_color = parse_color(_background_hex(bg_choice))
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
    heic_note = "HEIC/HEIF ready" if HEIC_SUPPORTED else "JPG and PNG ready"

    with gr.Blocks(title="Collage") as demo:
        input_folder = gr.State("")
        output_folder = gr.State("")

        gr.Markdown(
            f"# Collage\nTurn photo folders into clean image grids. {heic_note}.",
            elem_id="app-title",
        )

        with gr.Row(equal_height=True):
            with gr.Column(scale=3, min_width=320):
                input_summary = gr.HTML(_input_chip(""))
                choose_input_btn = gr.Button("Choose photos", variant="primary")
            with gr.Column(scale=3, min_width=320):
                output_summary = gr.HTML(_output_chip(""))
                choose_output_btn = gr.Button("Choose output")
            with gr.Column(scale=2, min_width=260):
                folder_status = gr.HTML(scan_folder("", False))
                scan_btn = gr.Button("Rescan")

        with gr.Accordion("Manual paths", open=False, elem_id="advanced-paths"):
            gr.Markdown("Paste paths here only if the folder buttons do not find what you need.")
            with gr.Row():
                input_path_box = gr.Textbox(label="Input path", placeholder="/path/to/photos")
                output_path_box = gr.Textbox(label="Output path", placeholder="/path/to/collages")

        with gr.Tabs():
            with gr.Tab("Layout"):
                with gr.Row():
                    layout_dd = gr.Radio(
                        LAYOUT_OPTIONS,
                        value="2x2",
                        label="Grid",
                        info="Columns x rows",
                    )
                    ratio_box = gr.Dropdown(
                        ["8.9:13.4", "1:1", "4:5", "9:16", "16:9"],
                        value="8.9:13.4",
                        allow_custom_value=True,
                        label="Shape",
                    )
                pixels_wide = gr.Slider(
                    minimum=800,
                    maximum=9600,
                    step=100,
                    value=4800,
                    label="Output width",
                    info="Higher values create larger JPEG files.",
                )

            with gr.Tab("Style"):
                fill_mode = gr.Radio(
                    ["fit", "cover"],
                    value="fit",
                    label="Image fill",
                    info="Fit keeps every image visible. Cover fills each cell and may crop edges.",
                )
                with gr.Row():
                    gap = gr.Slider(minimum=0, maximum=200, step=2, value=0, label="Gap")
                    border = gr.Slider(minimum=0, maximum=200, step=2, value=0, label="Border")
                bg_color = gr.Radio(
                    list(BG_OPTIONS),
                    value="White",
                    label="Background",
                    info="Used for gaps, borders, and empty cells.",
                )

            with gr.Tab("Sorting"):
                sort_mode = gr.Radio(
                    ["exif", "name"],
                    value="exif",
                    label="Order",
                    info="EXIF uses photo capture time when available.",
                )
                recursive = gr.Checkbox(value=False, label="Include subfolders")
                include_leftovers = gr.Checkbox(value=False, label="Create a final collage with leftover images")

        btn = gr.Button("Generate collages", variant="primary", elem_id="generate-btn")

        with gr.Row():
            gallery = gr.Gallery(
                label=f"Preview",
                columns=3,
                object_fit="contain",
                height=620,
                scale=3,
            )
            log_box = gr.Textbox(label="Run log", lines=12, interactive=False, scale=2)

        choose_input_btn.click(
            fn=choose_input_folder,
            inputs=[input_folder, output_folder, recursive],
            outputs=[input_folder, output_folder, input_summary, output_summary, folder_status],
        ).then(lambda value: value, inputs=input_folder, outputs=input_path_box).then(
            lambda value: value, inputs=output_folder, outputs=output_path_box
        )
        choose_output_btn.click(
            fn=choose_output_folder,
            inputs=output_folder,
            outputs=[output_folder, output_summary],
        ).then(lambda value: value, inputs=output_folder, outputs=output_path_box)
        scan_btn.click(
            fn=scan_folder,
            inputs=[input_folder, recursive],
            outputs=folder_status,
        )
        recursive.change(
            fn=scan_folder,
            inputs=[input_folder, recursive],
            outputs=folder_status,
        )
        input_path_box.change(
            fn=update_input_path,
            inputs=[input_path_box, output_folder, recursive],
            outputs=[input_folder, output_folder, input_summary, output_summary, folder_status],
        ).then(lambda value: value, inputs=output_folder, outputs=output_path_box)
        output_path_box.change(
            fn=update_output_path,
            inputs=output_path_box,
            outputs=[output_folder, output_summary],
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
        css=APP_CSS,
    )


if __name__ == "__main__":
    main()
