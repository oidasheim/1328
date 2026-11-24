import argparse
import json
from pathlib import Path

from synapse.models import Track
from synapse.pipeline import SynapsePipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a SYNAPSE production/release plan")
    parser.add_argument("track", type=Path)
    parser.add_argument("--artist", default="Unknown Artist")
    parser.add_argument("--title", default=None)
    parser.add_argument("--genre", default="")
    parser.add_argument("--out", type=Path, default=Path("reports/synapse_manifest.json"))
    parser.add_argument("--ledger", type=Path, default=Path("database/synapse_events.db"))
    args = parser.parse_args()

    track = Track(args.track, args.artist, args.title or args.track.stem, args.genre)
    pipeline = SynapsePipeline()
    manifest = pipeline.plan(track)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Created {args.out} with status: {manifest.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
