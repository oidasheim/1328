"""HTML and JSON reports for compilations and replayed decisions."""
from __future__ import annotations

from html import escape
import json
from pathlib import Path

from .models import RenderAST


def write_report(ast: RenderAST, destination: str | Path) -> Path:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    json_path = target.with_suffix(".json")
    json_path.write_text(json.dumps(ast.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rows = []
    for index, shot in enumerate(ast.shots):
        rows.append(f"<tr><td>{index}</td><td>{shot.timeline_start:.3f}</td><td>{shot.duration:.3f}</td><td>{escape(shot.clip_path)}</td><td>{escape(shot.camera)}</td><td>{escape(shot.color)}</td><td>{shot.score:.3f}</td></tr>")
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>WE.ED.IT Render Report</title>
<style>body{{font-family:system-ui;margin:2rem}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccc;padding:.45rem;text-align:left}}th{{background:#eee}}</style></head>
<body><h1>WE.ED.IT Render Report</h1><p>Duration: {ast.duration:.3f}s · {len(ast.shots)} shots · {ast.width}×{ast.height} @ {ast.fps} fps</p>
<table><thead><tr><th>Shot</th><th>Start</th><th>Duration</th><th>Clip</th><th>Camera</th><th>Color</th><th>Score</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<p><a href="{escape(json_path.name)}">Machine-readable AST</a></p></body></html>"""
    target.write_text(html, encoding="utf-8")
    return target
