#!/usr/bin/env bash
#
# Build the user manuals and publish the PDFs the Streamlit app serves.
#
# Each manual is manuals/<slug>/main.tex. This script builds every manual (skipping
# folders whose name starts with "_", e.g. _template) and copies the resulting PDF
# to static/manuals/<slug>.pdf — the path the app reads via manual_bytes(<slug>).
#
# Usage:
#   ./build.sh              build all manuals
#   ./build.sh <slug>       build just manuals/<slug>
#
# Requires a LaTeX toolchain (MacTeX/BasicTeX) on PATH; latexmk reads ./latexmkrc.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
DEST="$REPO_ROOT/static/manuals"
mkdir -p "$DEST"

# bibtex runs with its cwd inside each manual's build/ dir, so a relative bib path
# can't reach shared/. Hand it an absolute search path instead; main.tex then just
# says \bibliography{references}. (-r loads our latexmkrc regardless of cwd.)
export BIBINPUTS="$HERE/shared:${BIBINPUTS:-}"

only="${1:-}"
built=()

for dir in "$HERE"/manuals/*/; do
    slug="$(basename "$dir")"
    [[ "$slug" == _* ]] && continue                       # skip _template etc.
    [[ -n "$only" && "$slug" != "$only" ]] && continue
    [[ -f "$dir/main.tex" ]] || { echo "skip $slug (no main.tex)"; continue; }

    echo "==> building $slug"
    latexmk -r "$HERE/latexmkrc" -pdf -interaction=nonstopmode -halt-on-error "$dir/main.tex"

    pdf="$dir/build/main.pdf"
    if [[ -f "$pdf" ]]; then
        cp "$pdf" "$DEST/$slug.pdf"
        built+=("$slug")
    else
        echo "!! no PDF produced for $slug" >&2
        exit 1
    fi
done

if [[ -n "$only" && ${#built[@]} -eq 0 ]]; then
    echo "!! no manual named '$only' under manuals/" >&2
    exit 1
fi

echo
echo "Built ${#built[@]} manual(s): ${built[*]:-none}"
echo "PDFs published to static/manuals/"
