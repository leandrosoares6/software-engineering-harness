from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import Edge, Node


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    path TEXT,
    line INTEGER
);
CREATE TABLE IF NOT EXISTS edges (
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    kind TEXT NOT NULL,
    PRIMARY KEY (source, target, kind)
);
CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name);
CREATE INDEX IF NOT EXISTS idx_nodes_path ON nodes(path);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target);
"""


class GraphStore:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def replace_graph(self, nodes: list[Node], edges: list[Edge]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM edges")
            conn.execute("DELETE FROM nodes")
            conn.executemany(
                "INSERT INTO nodes(id, kind, name, path, line) VALUES (?, ?, ?, ?, ?)",
                [(n.id, n.kind.value, n.name, n.path, n.line) for n in nodes],
            )
            conn.executemany(
                "INSERT INTO edges(source, target, kind) VALUES (?, ?, ?)",
                [(e.source, e.target, e.kind.value) for e in edges],
            )

    def search_nodes(self, query: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT id, kind, name, path, line
                FROM nodes
                WHERE lower(name) LIKE lower(?) OR lower(path) LIKE lower(?)
                ORDER BY CASE WHEN lower(name) = lower(?) THEN 0 ELSE 1 END, name
                LIMIT 50
                """,
                (f"%{query}%", f"%{query}%", query),
            ).fetchall()

    def neighbors(self, node_id: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT e.kind AS edge_kind, 'out' AS direction, n.id AS id, n.kind AS node_kind, n.name AS name, n.path AS path, n.line AS line
                FROM edges e JOIN nodes n ON n.id = e.target WHERE e.source = ?
                UNION ALL
                SELECT e.kind AS edge_kind, 'in' AS direction, n.id AS id, n.kind AS node_kind, n.name AS name, n.path AS path, n.line AS line
                FROM edges e JOIN nodes n ON n.id = e.source WHERE e.target = ?
                ORDER BY edge_kind, direction, name
                """,
                (node_id, node_id),
            ).fetchall()
