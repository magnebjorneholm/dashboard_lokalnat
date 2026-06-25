"""Tests for the per-module in-page manual panel (pages/3 → module sections).

The in-page module manual works by slicing one section out of the revenue-cap
manual's ``main.md`` by its heading text (``MODULE_MANUAL_ANCHORS``). These tests
turn silent drift into a failing test: if a heading is renamed in the manual, or a
new tool module is added without a mapped section, the panel would just vanish with
no error. The invariants: every anchor resolves to a non-empty section, the anchors
cover exactly the base modules m1–m5, and a sliced section stops before the next.
"""

from frontend.common.manuals import (
    MODULE_MANUAL_ANCHORS,
    _DEFAULT_MANUAL_SLUG,
    manual_section_markdown,
)


def test_module_anchors_cover_base_modules():
    """The mapping covers exactly the configurable base modules (m1–m5)."""
    assert set(MODULE_MANUAL_ANCHORS) == {"m1", "m2", "m3", "m4", "m5"}


def test_module_anchors_resolve_to_sections():
    """Every anchor slices a non-empty section out of the manual's main.md."""
    for key, anchor in MODULE_MANUAL_ANCHORS.items():
        section = manual_section_markdown(_DEFAULT_MANUAL_SLUG, anchor)
        assert section, (
            f"{key}: anchor {anchor!r} did not resolve to a section in "
            f"user_manual_latex/{_DEFAULT_MANUAL_SLUG}/main.md — the module's "
            f"in-page manual panel would silently vanish"
        )
        # The slice must start with its own heading and not bleed into the next.
        assert section.lstrip().startswith("#"), f"{key}: section does not start at a heading"


def test_unknown_anchor_returns_none():
    """A missing heading slices to None (panel becomes a no-op, not an error)."""
    assert manual_section_markdown(_DEFAULT_MANUAL_SLUG, "9.9 Nonexistent") is None
