"""Run the portable setup and verification stages without external drive paths.

This orchestrator never posts, spends money, downloads models, or claims model
training. It creates local directories, initializes the SQLite genome and emits
measurements that can be reproduced on the current machine.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def run_command(label: str, args: list[str], cwd: Path = ROOT) -> dict[str, object]:
    start = time.perf_counter()
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    return {"stage": label, "status": "pass" if result.returncode == 0 else "warn",
            "return_code": result.returncode, "elapsed_seconds": round(time.perf_counter() - start, 4),
            "stdout": result.stdout[-4000:], "stderr": result.stderr[-4000:]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Portable WE.ED.IT batch setup and verification")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--install-deps", action="store_true", help="Install project test/vision extras with pip")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--keep-going", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    stages: list[dict[str, object]] = []
    for name in ("assets", "cache", "config", "database", "models", "output", "reports", "styles", "temp"):
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    stages.append({"stage": "directory-setup", "status": "pass", "root": str(ROOT)})

    if args.install_deps:
        stage = run_command("dependency-install", [sys.executable, "-m", "pip", "install", "-e", ".[test,vision]"])
        stages.append(stage)
        if stage["return_code"] and not args.keep_going:
            return _finish(stages, 1)

    commands = [
        ("doctor", [sys.executable, "-m", "weedit_native.cli", "doctor", "--deep"]),
        ("style-packages", None),
        ("invariants-verify", [sys.executable, "-m", "weedit_native.cli", "verify"]),
        ("sqlite-benchmark", [sys.executable, "-m", "weedit_native.cli", "benchmark", "--iterations", "250"]),
        ("genome-schema-upgrade", [sys.executable, "-c", "from weedit_native.genome import GenomeDB; db=GenomeDB('database/genome.sqlite3'); print({'clips':len(db.all())}); db.close()"]),
    ]
    for label, command in commands:
        if label == "style-packages":
            failed = False
            for style in ("drill", "trap", "cinematic", "horror", "anime", "musicvideo", "lofi"):
                stage = run_command(f"style-{style}", [sys.executable, "-m", "weedit_native.cli", "style", "install", style])
                stages.append(stage)
                failed |= stage["return_code"] != 0
            if failed and not args.keep_going:
                return _finish(stages, 1)
            continue
        stage = run_command(label, command)
        stages.append(stage)
        if stage["return_code"] and not args.keep_going and label not in {"doctor"}:
            return _finish(stages, 1)

    if not args.skip_tests:
        stage = run_command("tests", [sys.executable, "-m", "pytest", "tests", "-q"])
        if stage["return_code"] and "No module named pytest" in str(stage["stderr"]):
            stage["status"] = "warn"
            stage["message"] = "pytest is not installed; use pip install -e '.[test]'"
        stages.append(stage)

    # Do not label observed static inventory as learning or synthetic reward.
    database = ROOT / "database" / "genome.sqlite3"
    import sqlite3
    con = sqlite3.connect(database)
    try:
        clip_count = con.execute("SELECT COUNT(*) FROM clips").fetchone()[0]
        integrity = con.execute("PRAGMA quick_check").fetchone()[0]
    finally:
        con.close()
    stages.append({"stage": "knowledge-consolidation", "status": "pass" if integrity == "ok" else "fail",
                   "description": "inventory and schema report only; no model training or fabricated rewards",
                   "clip_count": clip_count, "sqlite_integrity": integrity})
    return _finish(stages, 1 if any(stage.get("status") == "fail" for stage in stages) else 0)


def _finish(stages: list[dict[str, object]], code: int) -> int:
    report = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "root": str(ROOT), "version": "0.8.0-portable-bootstrap", "stages": stages,
              "notes": ["No automatic posting, ad spend, model downloads, or blockchain operations.",
                        "Hardware and performance checks reflect this host only."]}
    reports = ROOT / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    target = reports / "portable-install-latest.json"
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
