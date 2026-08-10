from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class NodeKind(StrEnum):
    REPOSITORY = "repository"
    MODULE = "module"
    PACKAGE = "package"
    FILE = "file"
    CLASS = "class"
    INTERFACE = "interface"
    METHOD = "method"
    TEST = "test"


class EdgeKind(StrEnum):
    CONTAINS = "contains"
    IMPORTS = "imports"
    DECLARES = "declares"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    CALLS = "calls"
    TESTS = "tests"


@dataclass(frozen=True, slots=True)
class Node:
    id: str
    kind: NodeKind
    name: str
    path: str | None = None
    line: int | None = None


@dataclass(frozen=True, slots=True)
class Edge:
    source: str
    target: str
    kind: EdgeKind
