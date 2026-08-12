from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class NodeKind(StrEnum):
    REPOSITORY = "repository"
    MODULE = "module"
    PACKAGE = "package"
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    TEST = "test"


class EdgeKind(StrEnum):
    CONTAINS = "contains"
    IMPORTS = "imports"
    DECLARES = "declares"
    EXTENDS = "extends"
    CALLS = "calls"
    TESTS = "tests"


@dataclass(frozen=True, slots=True)
class Node:
    id: str
    kind: NodeKind
    name: str
    path: str | None = None
    line: int | None = None
    qualified_name: str | None = None
    signature: str | None = None


@dataclass(frozen=True, slots=True)
class Edge:
    source: str
    target: str
    kind: EdgeKind


@dataclass(frozen=True, slots=True)
class Diagnostic:
    kind: str
    message: str
    path: str | None = None
    line: int | None = None


@dataclass(frozen=True, slots=True)
class IndexMetadata:
    repository_root: str
    git_head: str | None
    fingerprint: str
    indexed_at: str
    indexer_version: str
    schema_version: int


@dataclass(frozen=True, slots=True)
class IndexResult:
    nodes: list[Node]
    edges: list[Edge]
    diagnostics: list[Diagnostic]

    def __iter__(self):
        yield self.nodes
        yield self.edges
