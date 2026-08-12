from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from . import __version__
from .capability_cli import configure_capability_parser
from .config import SehConfig
from .errors import IndexingError, SehError, StateError
from .git import head, repository_root, state_fingerprint
from .indexer import index_repository
from .models import IndexMetadata
from .storage import SCHEMA_VERSION, GraphStore


def _config(path: str | None, *, create: bool = False) -> SehConfig:
    root = repository_root(Path(path or "."))
    config = SehConfig.for_repo(root)
    if create:
        config.ensure()
    return config


def _validated_store(config: SehConfig) -> GraphStore:
    store = GraphStore(config.db_path)
    metadata = store.metadata()
    if not metadata.repository_root or not metadata.fingerprint:
        raise StateError("SEH is initialized but not indexed; run seh index")
    if Path(metadata.repository_root) != config.root:
        raise StateError("SEH index belongs to another repository; run seh index")
    if metadata.indexer_version != __version__:
        raise StateError("SEH index was built by another indexer version; run seh index")
    if metadata.fingerprint != state_fingerprint(config.root):
        raise StateError("SEH index is stale; run seh index")
    return store


def _location(row) -> str:
    return f"{row['path']}:{row['line']}" if row["line"] else row["path"] or "-"


def _print_candidate(row, *, file=sys.stdout) -> None:
    print(
        f"{row['id']:33} {row['kind']:12} {row['qualified_name']:48} {_location(row)}",
        file=file,
    )


def cmd_init(args: argparse.Namespace) -> int:
    config = _config(args.repo, create=True)
    GraphStore(config.db_path).initialize()
    config_file = config.state_dir / "config.json"
    if not config_file.exists():
        config_file.write_text(
            json.dumps({"seh": "0.1", "repository": config.root.name}, indent=2) + "\n",
            encoding="utf-8",
        )
    # Ignore this directory from inside it, so initializing SEH never dirties the
    # working tree and never edits a file the developer owns. A dirty tree would
    # otherwise block `capability capture`, which requires a provable baseline.
    ignore_file = config.state_dir / ".gitignore"
    if not ignore_file.exists():
        ignore_file.write_text("*\n", encoding="utf-8")
    print(f"Initialized SEH at {config.state_dir}")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    config = _config(args.repo, create=True)
    before = state_fingerprint(config.root)
    result = index_repository(config.root)
    after = state_fingerprint(config.root)
    if before != after:
        raise IndexingError("repository changed while indexing; run seh index again")
    metadata = IndexMetadata(
        repository_root=str(config.root),
        git_head=head(config.root),
        fingerprint=after,
        indexed_at=datetime.now(UTC).isoformat(),
        indexer_version=__version__,
        schema_version=SCHEMA_VERSION,
    )
    GraphStore(config.db_path).replace_graph(result.nodes, result.edges, metadata)
    revision = metadata.git_head[:12] if metadata.git_head else "unborn"
    print(f"Indexed {len(result.nodes)} nodes and {len(result.edges)} edges @ {revision}")
    if result.diagnostics:
        counts: dict[str, int] = {}
        for diagnostic in result.diagnostics:
            counts[diagnostic.kind] = counts.get(diagnostic.kind, 0) + 1
        summary = ", ".join(f"{kind}={count}" for kind, count in sorted(counts.items()))
        print(f"Warnings: {summary}", file=sys.stderr)
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    config = _config(args.repo)
    matches = _validated_store(config).search_nodes(args.query)
    if not matches:
        print("No matching symbols.")
        return 1
    for row in matches:
        _print_candidate(row)
    return 0


def cmd_neighbors(args: argparse.Namespace) -> int:
    config = _config(args.repo)
    store = _validated_store(config)
    if args.node_id:
        node = store.node(args.node_id)
        if node is None:
            print("No matching symbol.")
            return 1
    else:
        matches = store.search_nodes(args.query)
        if not matches:
            print("No matching symbols.")
            return 1
        if len(matches) > 1:
            print("Ambiguous symbol; choose one with --id:", file=sys.stderr)
            for candidate in matches:
                _print_candidate(candidate, file=sys.stderr)
            return 2
        node = matches[0]

    print(f"{node['kind']} {node['qualified_name']} ({node['id']})")
    for row in store.neighbors(node["id"]):
        arrow = "->" if row["direction"] == "out" else "<-"
        print(
            f"  {arrow} {row['edge_kind']:10} {row['node_kind']:12} "
            f"{row['qualified_name']} [{row['path'] or '-'}]"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seh", description="Software Engineering Harness")
    parser.add_argument("--version", action="version", version=__version__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    for name, handler in (("init", cmd_init), ("index", cmd_index)):
        command = subcommands.add_parser(name)
        command.add_argument("--repo")
        command.set_defaults(handler=handler)

    inspect_command = subcommands.add_parser("inspect")
    inspect_command.add_argument("query")
    inspect_command.add_argument("--repo")
    inspect_command.set_defaults(handler=cmd_inspect)

    neighbors_command = subcommands.add_parser("neighbors")
    selection = neighbors_command.add_mutually_exclusive_group(required=True)
    selection.add_argument("query", nargs="?")
    selection.add_argument("--id", dest="node_id")
    neighbors_command.add_argument("--repo")
    neighbors_command.set_defaults(handler=cmd_neighbors)

    configure_capability_parser(subcommands)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(args.handler(args))
    except SehError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
