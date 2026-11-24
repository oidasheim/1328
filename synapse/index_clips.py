"""Build/update a DuckDB OpenCLIP index from video middle frames."""
from __future__ import annotations

import argparse
from pathlib import Path

from .semantic_index import DuckDBSemanticIndex, encode_image, load_openclip

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


def read_middle_frame(path: Path):
    try:
        import cv2
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Install semantic extras: pip install '.[semantic]'") from exc
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return None, 0.0
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps and fps > 0 else 0.0
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_count // 2))
    ok, frame = cap.read()
    cap.release()
    if not ok or duration <= 0:
        return None, duration
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb), duration


def index_directory(clips_dir: Path, database: Path, device: str | None = None) -> tuple[int, int]:
    model_bundle = load_openclip(device)
    index = DuckDBSemanticIndex(database)
    indexed = skipped = 0
    try:
        for path in sorted(p for p in clips_dir.rglob("*") if p.suffix.lower() in VIDEO_EXTENSIONS):
            try:
                image, duration = read_middle_frame(path)
                if image is None:
                    skipped += 1
                    continue
                vector = encode_image(image, model_bundle)
                index.upsert(path, duration, vector)
                indexed += 1
            except (OSError, ValueError, RuntimeError) as exc:
                print(f"Skip {path}: {exc}")
                skipped += 1
    finally:
        index.close()
    return indexed, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clips_dir", type=Path)
    parser.add_argument("--db", type=Path, default=Path("database/clips_semantic.duckdb"))
    parser.add_argument("--device", choices=["cpu", "cuda"], default=None)
    args = parser.parse_args()
    if not args.clips_dir.is_dir():
        parser.error(f"Clip directory not found: {args.clips_dir}")
    indexed, skipped = index_directory(args.clips_dir, args.db, args.device)
    print(f"Indexing complete: {indexed} indexed, {skipped} skipped ({args.db})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
