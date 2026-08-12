from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from seh.errors import SchemaError, StateError, StorageError
from seh import __version__
from seh.models import Edge, EdgeKind, IndexMetadata, Node, NodeKind
from seh.storage import SCHEMA_VERSION, GraphStore


def metadata(root, fingerprint="abc") -> IndexMetadata:
    return IndexMetadata(
        repository_root=str(root.resolve()),
        git_head=None,
        fingerprint=fingerprint,
        indexed_at=datetime.now(UTC).isoformat(),
        indexer_version=__version__,
        schema_version=SCHEMA_VERSION,
    )


def test_store_roundtrip_with_metadata_and_foreign_keys(tmp_path):
    store = GraphStore(tmp_path / "seh.db")
    nodes = [
        Node("f1", NodeKind.FILE, "users.py", "src/app/users.py", qualified_name="src/app/users.py"),
        Node("c1", NodeKind.CLASS, "UserService", "src/app/users.py", 3, "app.users.UserService"),
    ]
    edges = [Edge("f1", "c1", EdgeKind.DECLARES)]
    store.replace_graph(nodes, edges, metadata(tmp_path))

    assert store.metadata().fingerprint == "abc"
    assert len(store.search_nodes("UserService")) == 1
    assert store.neighbors("f1")[0]["qualified_name"] == "app.users.UserService"
    with store.connect() as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_literal_wildcards_do_not_match_everything(tmp_path):
    store = GraphStore(tmp_path / "seh.db")
    store.replace_graph(
        [Node("f1", NodeKind.FILE, "100%real.py", "100%real.py", qualified_name="100%real.py")],
        [],
        metadata(tmp_path),
    )

    assert len(store.search_nodes("%")) == 1
    assert store.search_nodes("_") == []


def test_legacy_database_is_read_only_until_reindexed(tmp_path):
    path = tmp_path / "seh.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE nodes (id TEXT PRIMARY KEY)")
    store = GraphStore(path)

    with pytest.raises(SchemaError):
        store.metadata()

    store.replace_graph([], [], metadata(tmp_path))
    assert store.metadata().schema_version == SCHEMA_VERSION


def test_missing_database_read_does_not_create_file(tmp_path):
    path = tmp_path / "seh.db"

    with pytest.raises(StateError):
        GraphStore(path).metadata()

    assert not path.exists()


def test_unknown_node_returns_none(tmp_path):
    store = GraphStore(tmp_path / "seh.db")
    store.replace_graph([], [], metadata(tmp_path))

    assert store.node("missing") is None


def test_corrupt_database_raises_user_facing_storage_error(tmp_path):
    path = tmp_path / "seh.db"
    path.write_bytes(b"not a sqlite database")

    with pytest.raises(StorageError, match="schema"):
        GraphStore(path).metadata()


def test_failed_replacement_preserves_last_valid_graph(tmp_path):
    store = GraphStore(tmp_path / "seh.db")
    original = Node("f1", NodeKind.FILE, "original.py", "original.py", qualified_name="original.py")
    store.replace_graph([original], [], metadata(tmp_path, "original"))

    invalid_edge = Edge("missing", "also-missing", EdgeKind.CONTAINS)
    with pytest.raises(StorageError):
        store.replace_graph([], [invalid_edge], metadata(tmp_path, "replacement"))

    assert store.metadata().fingerprint == "original"
    assert store.node("f1")["name"] == "original.py"
