"""Tool registry — the single source of truth for Regumetrica's tools.

Pure data (no Streamlit), so it can drive the landing-page tools index now and
port directly to the future React landing (it is effectively a JSON structure).
Each tool ships its own manual PDF, served from ``static/manuals/<manual>.pdf``
(see ``frontend/common/manuals.py``).

Two branches mirror the authenticated tool zone's nav groups (see
``streamlit_app.py``): the core ``revenue_cap`` tool and the ``standalone`` tools.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional

ToolBranch = Literal["revenue_cap", "standalone"]
ToolStatus = Literal["available", "beta", "coming_soon"]


@dataclass(frozen=True)
class ToolSpec:
    """One tool. ``key`` is the stable id (also the future nav id)."""

    key: str
    name: str
    branch: ToolBranch
    summary: str                       # short, card-length description
    status: ToolStatus = "available"
    manual_slug: Optional[str] = None  # PDF slug; defaults to ``key``
    public: bool = True                # show on the public landing tools page
    page_path: Optional[str] = None    # st.Page path (for future nav unification)

    @property
    def manual(self) -> str:
        """Slug of this tool's manual PDF (``static/manuals/<manual>.pdf``)."""
        return self.manual_slug or self.key


# Order within a branch is the display order on the tools page.
TOOLS: List[ToolSpec] = [
    ToolSpec(
        key="revenue_cap",
        name="Revenue cap tool",
        branch="revenue_cap",
        status="available",
        manual_slug="regumetrica_user_manual",
        summary=(
            "Compute counterfactual revenue frames for a Swedish electricity "
            "distribution network. Work in <em>cases</em>, adjust the regulatory "
            "model's parameters and variables, run it, and compare the result "
            "against the baseline, component by component."
        ),
    ),
    ToolSpec(
        key="new_benchmarking_model",
        name="New benchmarking model",
        branch="standalone",
        status="available",
        summary=(
            "Explore Energimarknadsinspektionen's proposed TOTEX-based DEA "
            "benchmarking model and how it would change a network's efficiency "
            "requirement, now that a firm can be rewarded as well as penalised "
            "relative to the sector, all else equal."
        ),
    ),
    ToolSpec(
        key="placeholder",
        name="Placeholder",
        branch="standalone",
        status="coming_soon",
        summary="A future standalone analysis. Details will be announced here.",
        public=False,  # kept in the registry, but not rendered on the landing yet
    ),
]


def tools_for(branch: ToolBranch, *, public_only: bool = True) -> List[ToolSpec]:
    """Tools in a branch, in display order (public ones only by default)."""
    return [
        t for t in TOOLS
        if t.branch == branch and (t.public or not public_only)
    ]
