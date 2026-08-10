from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import SehConfig
from .git import GitError, assert_repo, head
from .indexer import index_repository
from .storage import GraphStore


def _config(path: str | None) -> SehConfig:
    root = Path(path or ".").resolve()
    assert_repo(root)
    config = SehConfig.for_repo(root)
    config.ensure()
    return config


def cmd_init(args: argparse.Namespace) -> int:
    config = _config(args.repo)
    GraphStore(config.db_path).init()
    config_file = config.state_dir / "config.json"
    if not config_file.exists():
        config_file.write_text(
            json.dumps({"seh": "0.1", "repository": config.root.name}, indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"Initialized SEH at {config.state_dir}")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    config = _config(args.repo)
    store = GraphStore(config.db_path)
    store.init()
    nodes, edges = index_repository(config.root)
    store.replace_graph(nodes, edges)
    print(f"Indexed {len(nodes)} nodes and {len(edges)} edges @ {head(config.root)[:12]}")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    config = _config(args.repo)
    store = GraphStore(config.db_path)
    store.init()
    matches = store.search_nodes(args.query)
    if not matches:
        print("No matching symbols.")
        return 1
    for row in matches:
        location = f"{row['path']}:{row['line']}" if row["line"] else row["path"] or "-"
        print(f"{row['kind']:10} {row['name']:40} {location}")
    return 0


def cmd_neighbors(args: argparse.Namespace) -> int:
    config = _config(args.repo)
    store = GraphStore(config.db_path)
    store.init()
    matches = store.search_nodes(args.query)
    if not matches:
        print("No matching symbols.")
        return 1
    node = matches[0]
    print(f"{node['kind']} {node['name']} ({node['id']})")
    for row in store.neighbors(node["id"]):
        arrow = "->" if row["direction"] == "out" else "<-"
        print(f"  {arrow} {row['edge_kind']:10} {row['node_kind']:10} {row['name']} [{row['path'] or '-'}]")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seh", description="Software Engineering Harness")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    for name, handler in (("init", cmd_init), ("index", cmd_index)):
        p = sub.add_parser(name)
        p.add_argument("--repo")
        p.set_defaults(handler=handler)

    p = sub.add_parser("inspect")
    p.add_argument("query")
    p.add_argument("--repo")
    p.set_defaults(handler=cmd_inspect)

    p = sub.add_parser("neighbors")
    p.add_argument("query")
    p.add_argument("--repo")
    p.set_defaults(handler=cmd_neighbors)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(args.handler(args))
    except GitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
