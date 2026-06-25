"""Access to the compiled user-manual PDFs.

Each tool ships its own manual. The LaTeX sources live in
``user_manual_latex/manuals/<slug>/`` and are built with ``user_manual_latex/build.sh``,
which publishes one PDF per tool to ``static/manuals/<slug>.pdf``. This module is the
single place the app reads those PDFs from — a landing page just calls
``manual_bytes("<slug>")`` (or renders a download with :func:`manual_download_button`).

Naming rule (must hold or a manual link silently disappears): the LaTeX folder name,
the published ``static/manuals/<slug>.pdf`` filename, and the registry's ``manual_slug``
(``config/tools_registry.py``) must all be the same ``<slug>``. build.sh couples the
first two (published name = folder basename); ``tests/test_tools_registry.py`` guards
the link to the registry.

Besides the published PDF, each manual keeps a Markdown twin of its source at
``user_manual_latex/manuals/<slug>/main.md``. The landing renders it in-page (an
``@st.dialog``) as an alternative to opening the PDF in a new window. It does so
through the **manual reader** (:func:`manual_reader_html`): a framework-agnostic
two-pane HTML document (sticky table of contents + scrolling content, with
click-to-scroll and scroll-spy) whose markup/behaviour live in
``static/manual_reader/`` and know nothing about Streamlit. This module is only the
host seam: it reads ``main.md`` (the content store), inlines the reader's CSS/JS,
loads the markdown/KaTeX libs from a pinned CDN, and injects the markdown plus the
Nordic-Energy theme tokens. A future React/Next.js landing reuses the same
``static/manual_reader/`` bundle and drops this builder. Same ``<slug>`` convention
as the PDF.
"""

import json
import re
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from config.colors import COLORS

MANUALS_DIR = Path("static/manuals")
# Manual sources (LaTeX + the Markdown twin) live one folder per tool here.
MANUALS_SRC_DIR = Path("user_manual_latex/manuals")
# Framework-agnostic reader bundle (CSS + behaviour). Inlined into the iframe today,
# importable as-is by a future React/Next.js port.
READER_DIR = Path("static/manual_reader")

# Third-party libs, pinned. Loaded from a CDN rather than vendored: a components.html
# iframe is served via srcdoc, where relative ``app/static/...`` paths do not resolve
# cleanly, and KaTeX drags a dozen font files — absolute CDN URLs sidestep both. A
# React port installs the same packages from npm at these versions. (Hardening TODO:
# add Subresource-Integrity hashes / vendor offline.)
_CDN = "https://cdn.jsdelivr.net/npm"
_KATEX_CSS = f"{_CDN}/katex@0.16.11/dist/katex.min.css"
_READER_SCRIPTS = (
    f"{_CDN}/markdown-it@14.1.0/dist/markdown-it.min.js",
    f"{_CDN}/markdown-it-anchor@9.2.0/dist/markdownItAnchor.umd.js",
    f"{_CDN}/katex@0.16.11/dist/katex.min.js",
    f"{_CDN}/markdown-it-texmath@1.0.0/texmath.js",
)
_FONTS = (
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700"
    "&family=IBM+Plex+Mono:wght@400;500&display=swap"
)

# Host -> reader theme bridge: map the app palette onto the reader's CSS variables
# (the reader ships Nordic-Energy defaults; this keeps it in lockstep with COLORS).
_THEME_VARS = {
    "--rm-primary": "primary",
    "--rm-text": "text_primary",
    "--rm-text2": "text_secondary",
    "--rm-muted": "text_muted",
    "--rm-card": "bg_card",
    "--rm-subtle": "bg_subtle",
    "--rm-border": "bg_muted",
    "--rm-warning": "warning",
    "--rm-warning-bg": "warning_light",
}


def manual_path(slug: str) -> Path:
    """Filesystem path to a tool's manual PDF (may not exist yet)."""
    return MANUALS_DIR / f"{slug}.pdf"


def manual_markdown_path(slug: str) -> Path:
    """Filesystem path to a tool's Markdown manual source (may not exist yet)."""
    return MANUALS_SRC_DIR / slug / "main.md"


@st.cache_data
def manual_bytes(slug: str) -> bytes | None:
    """Bytes of a tool's manual PDF, or ``None`` if it has not been built yet."""
    path = manual_path(slug)
    return path.read_bytes() if path.exists() else None


@st.cache_data
def manual_markdown(slug: str) -> str | None:
    """Markdown text of a tool's manual, or ``None`` if there is no ``main.md``."""
    path = manual_markdown_path(slug)
    return path.read_text(encoding="utf-8") if path.exists() else None


def _theme_root_block() -> str:
    """A ``:root`` override that maps the app palette onto the reader's CSS vars."""
    decls = "".join(
        f"{var}:{COLORS[key]};" for var, key in _THEME_VARS.items() if key in COLORS
    )
    return f":root{{{decls}}}"


def _build_reader_html(markdown_text: str, *, section_mode: bool = False) -> str:
    """Assemble the self-contained reader HTML document from a markdown string.

    Shared by the full-manual reader and the per-section reader. In ``section_mode``
    the table-of-contents pane is dropped (the root carries ``reader--section``) and
    a ``mode`` flag is handed to the bundle so it skips TOC/scroll-spy wiring and
    renders a single scrolling column.
    """
    reader_css = (READER_DIR / "reader.css").read_text(encoding="utf-8")
    reader_js = (READER_DIR / "reader.js").read_text(encoding="utf-8")

    # Safe embed in <script type="application/json">: escaping "</" keeps the JSON
    # from terminating the tag; JSON.parse reads "<\/" back as "</".
    payload = {"markdown": markdown_text}
    if section_mode:
        payload["mode"] = "section"
    data_json = json.dumps(payload).replace("</", "<\\/")
    scripts = "".join(f'<script src="{src}"></script>' for src in _READER_SCRIPTS)

    reader_class = "reader reader--section" if section_mode else "reader"
    toc = "" if section_mode else (
        '<nav class="reader-toc">'
        '<div class="reader-toc-label">Contents</div>'
        '<div class="reader-toc-list"></div>'
        '</nav>'
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{_FONTS}">
<link rel="stylesheet" href="{_KATEX_CSS}">
<style>{reader_css}</style>
<style>{_theme_root_block()}</style>
</head>
<body>
<div class="{reader_class}">
  {toc}
  <main class="reader-content"><article class="reader-article"></article></main>
</div>
<script type="application/json" id="manual-data">{data_json}</script>
{scripts}
<script>{reader_js}</script>
</body>
</html>"""


@st.cache_data
def manual_reader_html(slug: str) -> str | None:
    """Self-contained HTML document for a tool's in-page manual reader.

    Returns ``None`` if the tool has no ``main.md``. The result is a complete
    ``<html>`` document meant to be dropped into a ``components.html`` iframe: it
    pulls the markdown/KaTeX libs from a pinned CDN, inlines the framework-agnostic
    reader bundle (``static/manual_reader/reader.css`` + ``reader.js``), and injects
    the manual's markdown (as JSON) plus the app's theme tokens. The reader parses
    the markdown, builds the table of contents, and wires click-to-scroll and
    scroll-spy entirely client-side.
    """
    md = manual_markdown(slug)
    if md is None:
        return None
    return _build_reader_html(md)


def _strip_frontmatter(md: str) -> str:
    """Drop a leading ``--- ... ---`` frontmatter block (mirrors reader.js)."""
    m = re.match(r"^﻿?---\s*\n.*?\n---\s*\n?", md, re.DOTALL)
    return md[m.end():] if m else md


@st.cache_data
def manual_section_markdown(slug: str, section_anchor: str) -> str | None:
    """Slice one section out of a manual's ``main.md`` by its heading text.

    ``section_anchor`` is the raw heading text (without the leading ``#`` marks),
    e.g. ``"3.1 M1: Regulatory asset base valuation"``. Returns that heading plus
    everything beneath it up to the next heading of the same or higher level, or
    ``None`` if the manual or the heading is absent.
    """
    md = manual_markdown(slug)
    if md is None:
        return None

    lines = _strip_frontmatter(md).split("\n")
    target = section_anchor.strip()
    start = start_level = None
    for i, line in enumerate(lines):
        m = re.match(r"^(#{2,4})\s+(.*)$", line)
        if m and m.group(2).strip() == target:
            start, start_level = i, len(m.group(1))
            break
    if start is None:
        return None

    end = len(lines)
    for j in range(start + 1, len(lines)):
        m = re.match(r"^(#{1,6})\s+", lines[j])
        if m and len(m.group(1)) <= start_level:
            end = j
            break
    return "\n".join(lines[start:end]).strip() or None


@st.cache_data
def manual_section_reader_html(slug: str, section_anchor: str) -> str | None:
    """Single-section reader HTML (no TOC pane), for an in-page module panel.

    Returns ``None`` if the manual or the section is absent. Shares the reader
    bundle and theme bridge with :func:`manual_reader_html`; only the section's
    markdown is rendered, in the bundle's ``section`` mode.
    """
    section_md = manual_section_markdown(slug, section_anchor)
    if section_md is None:
        return None
    return _build_reader_html(section_md, section_mode=True)


# Map a tool module (config/module_registry key) onto the heading in the revenue-cap
# manual that documents it. Kept here (the manual seam), not in config/, so the config
# layer stays free of the manual's heading text. The values are the raw heading text in
# user_manual_latex/manuals/regumetrica_user_manual/main.md (guarded by tests).
_DEFAULT_MANUAL_SLUG = "regumetrica_user_manual"
MODULE_MANUAL_ANCHORS = {
    "m1": "3.1 M1: Regulatory asset base valuation",
    "m2": "3.2 M2: Depreciation",
    "m3": "3.3 M3: Cost of capital",
    "m4": "3.4 M4: Operating expenditures",
    "m5": "3.5 M5: Efficiency incentive (benchmarking)",
}


def module_manual_panel(
    module_key: str,
    *,
    manual_slug: str = _DEFAULT_MANUAL_SLUG,
    height: int = 460,
    expanded: bool = False,
    label: str = "User manual",
) -> None:
    """Render a collapsible in-page manual panel for one tool module.

    Slices the module's section out of the manual and shows it in the single-pane
    reader (no TOC) inside an ``st.expander``. A no-op if the module has no mapped
    section or the section/manual is missing — the panel simply does not appear.

    This is the only host-specific seam: swapping the expander for an ``st.dialog``
    or ``st.popover`` later is a change to this function alone.
    """
    anchor = MODULE_MANUAL_ANCHORS.get(module_key)
    if anchor is None:
        return
    html = manual_section_reader_html(manual_slug, anchor)
    if html is None:
        return
    with st.expander(label, expanded=expanded):
        components.html(html, height=height, scrolling=False)


def manual_download_button(
    slug: str,
    *,
    label: str = "Download the manual (PDF)",
    file_name: str | None = None,
    missing_message: str = "The user manual will be available here shortly.",
) -> None:
    """Render a primary download button for a tool's manual, or an info note if absent.

    ``file_name`` defaults to ``<slug>.pdf``; pass a friendlier name for the download.
    """
    pdf = manual_bytes(slug)
    if pdf:
        st.download_button(
            label,
            data=pdf,
            file_name=file_name or f"{slug}.pdf",
            mime="application/pdf",
            type="primary",
            width="stretch",
        )
    else:
        st.info(missing_message)
