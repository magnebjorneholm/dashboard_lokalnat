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
``@st.dialog``) as an alternative to opening the PDF in a new window;
:func:`manual_markdown` reads it. Same ``<slug>`` convention as the PDF.
"""

from pathlib import Path

import streamlit as st

MANUALS_DIR = Path("static/manuals")
# Manual sources (LaTeX + the Markdown twin) live one folder per tool here.
MANUALS_SRC_DIR = Path("user_manual_latex/manuals")


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
