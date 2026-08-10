from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .git import tracked_files
from .models import Edge, EdgeKind, Node, NodeKind

JAVA_TYPE = re.compile(
    r"\b(?P<kind>class|interface)\s+(?P<name>[A-Za-z_$][\w$]*)"
    r"(?:\s+extends\s+(?P<extends>[A-Za-z_$][\w$\.]*))?"
    r"(?:\s+implements\s+(?P<implements>[A-Za-z_$][\w$\.,\s]*))?"
)
JAVA_METHOD = re.compile(
    r"^(?:\s*)(?:public|protected|private|static|final|synchronized|abstract|native|default|strictfp|\s)+"
    r"(?:<[^>]+>\s+)?[\w$<>, ?\[\].]+\s+(?P<name>[A-Za-z_$][\w$]*)\s*\([^;]*\)\s*(?:throws [^{]+)?\{?"
)
JAVA_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?(?P<name>[\w$.]+)\s*;")


def _id(kind: str, value: str) -> str:
    digest = hashlib.sha1(f"{kind}:{value}".encode()).hexdigest()[:16]
    return f"{kind}:{digest}"


def _is_test(path: Path) -> bool:
    normalized = path.as_posix().lower()
    return "/test/" in normalized or path.stem.endswith(("Test", "Tests", "IT"))


def index_repository(root: Path) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    by_simple_name: dict[str, str] = {}
    pending_relations: list[tuple[str, EdgeKind, str]] = []

    repo_id = _id("repository", str(root.resolve()))
    nodes.append(Node(repo_id, NodeKind.REPOSITORY, root.name, str(root)))

    files = [p for p in tracked_files(root) if p.is_file()]
    for path in files:
        rel = path.relative_to(root).as_posix()
        file_id = _id("file", rel)
        kind = NodeKind.TEST if _is_test(path) else NodeKind.FILE
        nodes.append(Node(file_id, kind, path.name, rel))
        edges.append(Edge(repo_id, file_id, EdgeKind.CONTAINS))

        if path.suffix != ".java":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        current_type_id: str | None = None
        for lineno, line in enumerate(text.splitlines(), start=1):
            if match := JAVA_IMPORT.match(line):
                pending_relations.append((file_id, EdgeKind.IMPORTS, match.group("name").split(".")[-1]))
                continue

            if match := JAVA_TYPE.search(line):
                type_name = match.group("name")
                type_kind = NodeKind.CLASS if match.group("kind") == "class" else NodeKind.INTERFACE
                current_type_id = _id(type_kind.value, f"{rel}:{type_name}")
                nodes.append(Node(current_type_id, type_kind, type_name, rel, lineno))
                by_simple_name[type_name] = current_type_id
                edges.append(Edge(file_id, current_type_id, EdgeKind.DECLARES))
                if match.group("extends"):
                    pending_relations.append((current_type_id, EdgeKind.EXTENDS, match.group("extends").split(".")[-1]))
                if match.group("implements"):
                    for name in match.group("implements").split(","):
                        pending_relations.append((current_type_id, EdgeKind.IMPLEMENTS, name.strip().split(".")[-1]))
                continue

            if current_type_id and (match := JAVA_METHOD.match(line)):
                method_name = match.group("name")
                method_id = _id("method", f"{rel}:{lineno}:{method_name}")
                nodes.append(Node(method_id, NodeKind.METHOD, method_name, rel, lineno))
                edges.append(Edge(current_type_id, method_id, EdgeKind.CONTAINS))

    for source, kind, target_name in pending_relations:
        target = by_simple_name.get(target_name)
        if target:
            edges.append(Edge(source, target, kind))

    return nodes, edges
