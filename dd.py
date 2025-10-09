import os
from pathlib import Path

def print_tree(directory, prefix="", ignore=["__pycache__", ".git", "venv", "env", ".pyc"]):
    contents = sorted(Path(directory).iterdir(), key=lambda x: (not x.is_dir(), x.name))
    contents = [c for c in contents if not any(ig in str(c) for ig in ignore)]
    
    for i, path in enumerate(contents):
        is_last = i == len(contents) - 1
        print(f"{prefix}{'└── ' if is_last else '├── '}{path.name}")
        if path.is_dir() and len(list(path.iterdir())) > 0:
            print_tree(path, prefix + ("    " if is_last else "│   "), ignore)

print_tree(".")
