"""CLI for Platform Relations Vector routing and governance simulation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .platform_relations import PlatformRelationsGraph, write_graph


def main() -> int:
    parser = argparse.ArgumentParser(prog="synapse-platform-vector")
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export")
    export.add_argument("--out", type=Path, default=Path("reports/platform_vector.json"))
    route = sub.add_parser("route")
    route.add_argument("asset_id")
    route.add_argument("--target", action="append", required=True)
    route.add_argument("--affinity", type=float, default=0.5)
    route.add_argument("--freshness", type=float, default=0.5)
    gate = sub.add_parser("gate")
    gate.add_argument("asset_id")
    gate.add_argument("--approved", action="store_true")
    gate.add_argument("--human-confirmed", action="store_true")
    gate.add_argument("--rights-verified", action="store_true")
    gate.add_argument("--qc-passed", action="store_true")
    gate.add_argument("--status", choices=("approve", "hold", "reject"), default="hold")
    args = parser.parse_args()
    graph = PlatformRelationsGraph()
    if args.command == "export":
        print(write_graph(args.out, graph))
    elif args.command == "route":
        print(json.dumps([item.__dict__ for item in graph.recommend(
            args.asset_id, args.target, args.affinity, args.freshness)], indent=2))
    else:
        print(json.dumps(graph.apply_publisher_gate(
            args.asset_id, args.approved, args.human_confirmed,
            args.rights_verified, args.qc_passed, args.status).__dict__, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
