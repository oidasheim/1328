#!/usr/bin/env python3
"""Discover local Python install candidates and optionally install into ./.venv.

Default behavior is a dry-run. Only pass --install to execute pip. No global
site-packages are modified; all installs target the repository-local venv.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import venv

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "__pycache__",
    "node_modules", "vendor", "dist", "build", ".tox", ".mypy_cache",
}
PACKAGE_MARKERS = ("pyproject.toml", "setup.py", "setup.cfg")
REQUIREMENTS_MARKERS = ("requirements.txt", "requirements-dev.txt")


def discover(root: Path) -> list[tuple[Path, str, Path]]:
    """Return (directory, candidate kind, manifest) entries under root."""
    found: dict[Path, tuple[Path, str, Path]] = {}
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        directory = Path(current).resolve()

        marker = next((name for name in PACKAGE_MARKERS if name in files), None)
        if marker:
            found[directory] = (directory, "editable", directory / marker)
            continue

        requirement = next((name for name in REQUIREMENTS_MARKERS if name in files), None)
        if requirement:
            found[directory] = (directory, "requirements", directory / requirement)

    return sorted(found.values(), key=lambda item: (len(item[0].parts), str(item[0])))


def ensure_venv(path: Path) -> Path:
    if not (path / "pyvenv.cfg").exists():
        venv.EnvBuilder(with_pip=True).create(path)
    if os.name == "nt":
        return path / "Scripts" / "python.exe"
    return path / "bin" / "python"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--venv", type=Path, default=None,
                        help="Local virtualenv path (default: <root>/.venv)")
    parser.add_argument("--install", action="store_true",
                        help="Actually install discovered candidates; default is dry-run")
    args = parser.parse_args()

    root = args.root.resolve()
    venv_path = (args.venv or root / ".venv").resolve()
    if not root.is_dir():
        parser.error(f"Root directory does not exist: {root}")
    if venv_path != root and root not in venv_path.parents:
        parser.error("The virtualenv must be inside the selected project root")

    candidates = discover(root)
    if not candidates:
        print(f"No Python install candidates found under {root}")
        return 0

    print(f"Found {len(candidates)} candidate(s) under {root}:")
    for directory, kind, manifest in candidates:
        print(f"- {directory.relative_to(root)} [{kind}: {manifest.name}]")

    if not args.install:
        print("Dry-run only. Re-run with --install to install into the local .venv.")
        return 0

    python = ensure_venv(venv_path)
    for directory, kind, manifest in candidates:
        if kind == "editable":
            command = [str(python), "-m", "pip", "install", "--editable", str(directory)]
        else:
            command = [str(python), "-m", "pip", "install", "--requirement", str(manifest)]
        print("+", " ".join(command))
        subprocess.run(command, check=True, cwd=root)

    print(f"Installed discovered candidates into {venv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
