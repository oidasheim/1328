# Local package setup and recursive candidate installation

This repository is now installable as a local Python package. It requires Python
3.10+ and has no mandatory third-party runtime dependencies.

Discover local Python packages and requirements files without changing anything:

```bash
python scripts/install_candidates.py
```

Install discovered editable packages and requirements into the repository-local
`.venv` (never global Python):

```bash
python scripts/install_candidates.py --install
```

The scanner excludes virtual environments, VCS metadata, build outputs, vendor
folders, and hidden directories. It recognizes `pyproject.toml`, `setup.py`,
`setup.cfg`, `requirements.txt`, and `requirements-dev.txt`. Review discovered
candidates before using `--install`, since package build scripts and dependency
installation can execute code and access configured package indexes.

Install only this project and its CLI directly:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\python.exe -m pip install -e .
# Linux/macOS: .venv/bin/python -m pip install -e .
```
