from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

from . import __version__
from .errors import SchemaError, StateError, StorageError
from .models import Edge, IndexMetadata, Node

SCHEMA_VERSION = 2
SCHEMA = f"""
PRAGMA foreign_keys = ON;
CREATE TABLE nodes (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    signature TEXT,
    path TEXT,
    line INTEGER
);
CREATE TABLE edges (
    source TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    PRIMARY KEY (source, target, kind)
);
CREATE TABLE metadata (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    repository_root TEXT NOT NULL,
    git_head TEXT,
    fingerprint TEXT NOT NULL,
    indexed_at TEXT NOT NULL,
    indexer_version TEXT NOT NULL,
    schema_version INTEGER NOT NULL
);
CREATE INDEX idx_nodes_name ON nodes(name);
CREATE INDEX idx_nodes_qualified_name ON nodes(qualified_name);
CREATE INDEX idx_nodes_path ON nodes(path);
CREATE INDEX idx_edges_source ON edges(source);
CREATE INDEX idx_edges_target ON edges(target);
PRAGMA user_version = {SCHEMA_VERSION};
"""


class GraphStore:
    def __init__(self, path: Path):
        self.path = path

    def connect(self, *, readonly: bool = False) -> sqlite3.Connection:
        try:
            if readonly:
                if not self.path.is_file():
                    raise StateError("SEH is not indexed; run seh index")
                connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
            else:
                connection = sqlite3.connect(self.path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            return connection
        except sqlite3.Error as exc:
            raise StorageError(f"unable to open graph store: {exc}") from exc

    def initialize(self) -> None:
        if self.path.exists():
            self._require_current_schema()
            return
        self.replace_graph(
            [],
            [],
            IndexMetadata("", None, "", "", __version__, SCHEMA_VERSION),
        )

    def _require_current_schema(self) -> None:
        try:
            with self.connect(readonly=True) as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
        except sqlite3.Error as exc:
            raise StorageError(f"unable to inspect graph schema: {exc}") from exc
        if version != SCHEMA_VERSION:
            raise SchemaError(
                f"unsupported graph schema {version}; run seh index to rebuild it"
            )

    def replace_graph(
        self,
        nodes: list[Node],
        edges: list[Edge],
        metadata: IndexMetadata,
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        try:
            with sqlite3.connect(temporary_path) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.executescript(SCHEMA)
                connection.executemany(
                    """
                    INSERT INTO nodes(id, kind, name, qualified_name, signature, path, line)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            node.id,
                            node.kind.value,
                            node.name,
                            node.qualified_name or node.name,
                            node.signature,
                            node.path,
                            node.line,
                        )
                        for node in nodes
                    ],
                )
                connection.executemany(
                    "INSERT INTO edges(source, target, kind) VALUES (?, ?, ?)",
                    [(edge.source, edge.target, edge.kind.value) for edge in edges],
                )
                connection.execute(
                    """
                    INSERT INTO metadata(
                        singleton, repository_root, git_head, fingerprint,
                        indexed_at, indexer_version, schema_version
                    ) VALUES (1, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        metadata.repository_root,
                        metadata.git_head,
                        metadata.fingerprint,
                        metadata.indexed_at,
                        metadata.indexer_version,
                        metadata.schema_version,
                    ),
                )
            os.replace(temporary_path, self.path)
        except (OSError, sqlite3.Error) as exc:
            raise StorageError(f"unable to replace graph store: {exc}") from exc
        finally:
            temporary_path.unlink(missing_ok=True)

    def metadata(self) -> IndexMetadata:
        self._require_current_schema()
        try:
            with self.connect(readonly=True) as connection:
                row = connection.execute(
                    """
                    SELECT repository_root, git_head, fingerprint, indexed_at,
                           indexer_version, schema_version
                    FROM metadata WHERE singleton = 1
                    """
                ).fetchone()
        except sqlite3.Error as exc:
            raise StorageError(f"unable to read graph metadata: {exc}") from exc
        if row is None:
            raise StateError("SEH index metadata is missing; run seh index")
        return IndexMetadata(**dict(row))

    def search_nodes(self, query: str) -> list[sqlite3.Row]:
        self._require_current_schema()
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        try:
            with self.connect(readonly=True) as connection:
                return connection.execute(
                    """
                    SELECT id, kind, name, qualified_name, signature, path, line
                    FROM nodes
                    WHERE lower(name) LIKE lower(?) ESCAPE '\\'
                       OR lower(qualified_name) LIKE lower(?) ESCAPE '\\'
                       OR lower(path) LIKE lower(?) ESCAPE '\\'
                    ORDER BY CASE WHEN lower(qualified_name) = lower(?) THEN 0
                                  WHEN lower(name) = lower(?) THEN 1 ELSE 2 END,
                             qualified_name, path, line
                    LIMIT 50
                    """,
                    (pattern, pattern, pattern, query, query),
                ).fetchall()
        except sqlite3.Error as exc:
            raise StorageError(f"unable to search graph nodes: {exc}") from exc

    def node(self, node_id: str) -> sqlite3.Row | None:
        self._require_current_schema()
        try:
            with self.connect(readonly=True) as connection:
                return connection.execute(
                    """
                    SELECT id, kind, name, qualified_name, signature, path, line
                    FROM nodes WHERE id = ?
                    """,
                    (node_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise StorageError(f"unable to read graph node: {exc}") from exc

    def neighbors(self, node_id: str) -> list[sqlite3.Row]:
        self._require_current_schema()
        try:
            with self.connect(readonly=True) as connection:
                return connection.execute(
                    """
                    SELECT e.kind AS edge_kind, 'out' AS direction, n.id AS id,
                           n.kind AS node_kind, n.name AS name,
                           n.qualified_name AS qualified_name, n.signature AS signature,
                           n.path AS path, n.line AS line
                    FROM edges e JOIN nodes n ON n.id = e.target WHERE e.source = ?
                    UNION ALL
                    SELECT e.kind AS edge_kind, 'in' AS direction, n.id AS id,
                           n.kind AS node_kind, n.name AS name,
                           n.qualified_name AS qualified_name, n.signature AS signature,
                           n.path AS path, n.line AS line
                    FROM edges e JOIN nodes n ON n.id = e.source WHERE e.target = ?
                    ORDER BY edge_kind, direction, qualified_name
                    """,
                    (node_id, node_id),
                ).fetchall()
        except sqlite3.Error as exc:
            raise StorageError(f"unable to read graph neighbors: {exc}") from exc
