#!/usr/bin/env python3
"""
find_unused_files.py

Analyserar repo för att hitta Python-moduler, text- och datafiler som inte refereras
via statiska imports eller filvägssträngar.

Usage:
  python3 find_unused_files.py [root]

Notera: statisk analys — dynamiska imports och filvägar kan missa användning.
Skriptet skapar en rapport i stdout med två listor: använda och oanvända filer.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict, Set, List, Tuple

IMPORT_RE = re.compile(r"^(?:from|import)\s+([\w\.]+)")
FROM_RE = re.compile(r"^from\s+([\w\.]+)\s+import")
IMPORT_LINE_RE = re.compile(r"^import\s+([\w\.]+)")
STRING_PATH_RE = re.compile(r"[\'\"]([^\'\"]+\.[a-zA-Z0-9]{1,5})[\'\"]")

DATA_EXTS = {'.parquet', '.xlsx', '.xls', '.csv'}
TEXT_EXTS = {'.txt'}
EXCLUDE_DIRS = {'venv', '.venv', 'node_modules', '.git', '__pycache__'}


def list_files(root: Path) -> Tuple[List[Path], List[Path], List[Path]]:
    py_files = []
    text_files = []
    data_files = []
    for p in root.rglob('*'):
        # skip virtualenvs, node_modules, git metadata and cache dirs
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if p.is_file():
            ext = p.suffix.lower()
            if ext == '.py':
                py_files.append(p)
            elif ext in TEXT_EXTS:
                text_files.append(p)
            elif ext in DATA_EXTS:
                data_files.append(p)
    return py_files, text_files, data_files


def module_name_from_path(root: Path, p: Path) -> str:
    # Convert path relative to root to module path
    rel = p.relative_to(root).with_suffix('')
    parts = rel.parts
    return '.'.join(parts)


def parse_imports(p: Path) -> Set[str]:
    mods = set()
    try:
        text = p.read_text(encoding='utf-8')
    except Exception:
        return mods
    for line in text.splitlines():
        line = line.strip()
        m = FROM_RE.match(line)
        if m:
            mods.add(m.group(1))
            continue
        m2 = IMPORT_LINE_RE.match(line)
        if m2:
            mods.add(m2.group(1))
    return mods


def find_string_paths(p: Path) -> Set[str]:
    out = set()
    try:
        text = p.read_text(encoding='utf-8')
    except Exception:
        return out
    for m in STRING_PATH_RE.finditer(text):
        out.add(m.group(1))
    return out


def build_module_map(root: Path, py_files: List[Path]) -> Dict[str, Path]:
    mm = {}
    for p in py_files:
        mod = module_name_from_path(root, p)
        mm[mod] = p
    return mm


def resolve_import_to_file(mod_name: str, module_map: Dict[str, Path]) -> Path | None:
    # try direct match, then progressively shorten
    if mod_name in module_map:
        return module_map[mod_name]
    # try prefixes
    parts = mod_name.split('.')
    for i in range(len(parts), 0, -1):
        candidate = '.'.join(parts[:i])
        if candidate in module_map:
            return module_map[candidate]
    return None


def detect_entry_points(py_files: List[Path], root: Path) -> List[Path]:
    entries = []
    for p in py_files:
        try:
            txt = p.read_text(encoding='utf-8')
        except Exception:
            continue
        if '__main__' in txt or 'streamlit_app' in p.name or p.parent.name == 'pages' or 'st.set_page_config' in txt:
            entries.append(p)
    # Ensure common known entry points
    known = ['streamlit_app.py', 'dash/app.py', 'Moran/moran_run.py', 'dd.py']
    for k in known:
        kp = root.joinpath(k)
        if kp.exists() and kp not in entries:
            entries.append(kp)
    return entries


def main(root_str: str = '.'):
    root = Path(root_str).resolve()
    print(f'Analyzing repo root: {root}')

    py_files, text_files, data_files = list_files(root)
    print(f'Found {len(py_files)} Python files, {len(text_files)} text files, {len(data_files)} data files')

    module_map = build_module_map(root, py_files)

    # parse imports and string paths
    imports_map: Dict[Path, Set[str]] = {}
    string_paths_map: Dict[Path, Set[str]] = {}
    for p in py_files:
        imports_map[p] = parse_imports(p)
        string_paths_map[p] = find_string_paths(p)

    # build reverse mapping of module -> files that import it
    module_rev: Dict[str, Set[Path]] = {}
    for p, mods in imports_map.items():
        for m in mods:
            module_rev.setdefault(m, set()).add(p)

    # Determine entry points
    entries = detect_entry_points(py_files, root)
    print('Detected entry points:')
    for e in entries:
        print(' -', e.relative_to(root))

    # BFS over imports to find reachable files
    reachable: Set[Path] = set()
    queue: List[Path] = []
    for e in entries:
        if e.exists():
            reachable.add(e)
            queue.append(e)

    while queue:
        cur = queue.pop(0)
        mods = imports_map.get(cur, set())
        for m in mods:
            f = resolve_import_to_file(m, module_map)
            if f and f not in reachable:
                reachable.add(f)
                queue.append(f)

    # Also treat files imported by relative module names (e.g. foretag.view.*)
    # For safety, mark any file that is imported by name occurrence in any py file as reachable
    all_text = '\n'.join([p.read_text(encoding='utf-8', errors='ignore') for p in py_files])
    for p in py_files:
        mod = module_name_from_path(root, p)
        if mod in all_text:
            reachable.add(p)

    # Mark data files as used if their relative path or filename appears in any .py
    used_data: Set[Path] = set()
    for d in data_files:
        rel = str(d.relative_to(root))
        basename = d.name
        if rel in all_text or basename in all_text:
            used_data.add(d)

    # Text files referenced?
    used_text: Set[Path] = set()
    for t in text_files:
        rel = str(t.relative_to(root))
        basename = t.name
        if rel in all_text or basename in all_text:
            used_text.add(t)

    # Results
    unused_py = sorted([p for p in py_files if p not in reachable])
    unused_data = sorted([d for d in data_files if d not in used_data])
    unused_text = sorted([t for t in text_files if t not in used_text])

    print('\n=== Reachable Python files (count) ===')
    print(len(reachable))
    for p in sorted(reachable):
        try:
            print('-', p.relative_to(root))
        except Exception:
            print('-', p)

    print('\n=== Unused Python files candidates ===')
    for p in unused_py:
        print('-', p.relative_to(root))

    print('\n=== Unused data files candidates ===')
    for d in unused_data:
        print('-', d.relative_to(root))

    print('\n=== Unused text files candidates ===')
    for t in unused_text:
        print('-', t.relative_to(root))

    # Return codes
    return 0


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    sys.exit(main(root))