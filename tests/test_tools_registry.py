"""Tests for the tool registry ↔ published-manual consistency.

These turn silent drift into a failing test: if a tool's ``manual_slug`` stops
matching its published PDF (renamed LaTeX folder, forgotten build, typo), the
manual link would just vanish from the tools page with no error. The invariant
is: every ``available`` tool has a published manual; ``coming_soon`` does not.
"""

from pathlib import Path

from config.tools_registry import TOOLS
from frontend.common.manuals import MANUALS_DIR, manual_markdown_path, manual_path


def test_available_tools_have_published_manuals():
    """Every available tool's manual PDF exists in static/manuals/."""
    for t in TOOLS:
        if t.status == "available":
            assert manual_path(t.manual).exists(), (
                f"{t.key}: status is 'available' but "
                f"static/manuals/{t.manual}.pdf is missing — "
                f"run user_manual_latex/build.sh {t.manual}"
            )


def test_available_tools_have_markdown_twin():
    """Every available tool has a main.md so the landing's in-page reader works."""
    for t in TOOLS:
        if t.status == "available":
            assert manual_markdown_path(t.manual).exists(), (
                f"{t.key}: status is 'available' but "
                f"user_manual_latex/manuals/{t.manual}/main.md is missing — "
                f"the 'Read in page' link would silently vanish"
            )


def test_no_orphan_published_manuals():
    """Every published PDF maps to a registered tool (catches renamed slugs)."""
    registered = {t.manual for t in TOOLS}
    for pdf in MANUALS_DIR.glob("*.pdf"):
        assert pdf.stem in registered, (
            f"orphan manual: static/manuals/{pdf.name} has no tool in TOOLS "
            f"with manual_slug='{pdf.stem}'"
        )


def test_tool_keys_are_unique():
    """Keys are stable ids — they must not collide."""
    keys = [t.key for t in TOOLS]
    assert len(keys) == len(set(keys)), "duplicate tool key in TOOLS"
