from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .git import repository_root, tracked_files
from .models import Diagnostic, Edge, EdgeKind, IndexResult, Node, NodeKind
from .python_adapter import ImportDecl, PythonAdapter, PythonDocument, SymbolDecl


def _id(kind: str, value: str) -> str:
    digest = hashlib.sha256(f"{kind}:{value}".encode()).hexdigest()[:20]
    return f"{kind}:{digest}"


def _is_test(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    return bool(parts & {"test", "tests"}) or path.stem.startswith("test_") or path.stem.endswith("_test")


def _module_name(relative: str, package_dirs: set[PurePosixPath]) -> str:
    path = PurePosixPath(relative)
    directories = list(path.parent.parts) if path.parent != PurePosixPath(".") else []
    stem = path.stem

    start = 0
    for index in range(len(directories)):
        suffixes = [PurePosixPath(*directories[: position + 1]) for position in range(index, len(directories))]
        if suffixes and all(item in package_dirs for item in suffixes):
            start = index
            break
    else:
        if directories and directories[0] == "src":
            start = 1

    parts = directories[start:]
    if stem != "__init__":
        parts.append(stem)
    return ".".join(parts) or stem


@dataclass(frozen=True, slots=True)
class PendingBase:
    source: str
    expression: str
    document: PythonDocument


class SymbolCatalog:
    def __init__(self, declarations: list[tuple[SymbolDecl, str]]) -> None:
        self.by_qualified: dict[str, list[str]] = defaultdict(list)
        for declaration, node_id in declarations:
            self.by_qualified[declaration.qualified_name].append(node_id)

    def resolve(self, expression: str, document: PythonDocument) -> tuple[str | None, str]:
        aliases: dict[str, str] = {}
        for imported in document.imports:
            if imported.wildcard:
                continue
            target = f"{imported.module}.{imported.name}" if imported.name else imported.module
            aliases[imported.alias] = target

        head, separator, tail = expression.partition(".")
        candidates: list[str] = []
        if head in aliases:
            candidates.append(aliases[head] + (f".{tail}" if separator else ""))
        if separator:
            candidates.append(expression)
        else:
            candidates.append(f"{document.module}.{expression}")
            candidates.append(expression)

        seen: set[str] = set()
        matches: list[str] = []
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            matches.extend(self.by_qualified.get(candidate, []))
        if len(matches) == 1:
            return matches[0], "resolved"
        if len(matches) > 1:
            return None, "ambiguous"
        return None, "unresolved"


def index_repository(root: Path) -> IndexResult:
    root = repository_root(root)
    paths = [path for path in tracked_files(root) if path.is_file()]
    python_paths = [path for path in paths if path.suffix == ".py"]
    package_dirs = {
        PurePosixPath(path.relative_to(root).as_posix()).parent
        for path in python_paths
        if path.name == "__init__.py"
    }

    nodes: list[Node] = []
    edges: list[Edge] = []
    diagnostics: list[Diagnostic] = []
    repo_id = _id("repository", str(root))
    nodes.append(Node(repo_id, NodeKind.REPOSITORY, root.name, str(root), qualified_name=str(root)))

    adapter = PythonAdapter()
    documents: list[tuple[PythonDocument, str]] = []
    declarations: list[tuple[SymbolDecl, str]] = []
    pending: list[PendingBase] = []
    module_ids: dict[str, str] = {}

    for path in paths:
        relative = path.relative_to(root).as_posix()
        file_id = _id("file", relative)
        file_kind = NodeKind.TEST if _is_test(path.relative_to(root)) else NodeKind.FILE
        nodes.append(Node(file_id, file_kind, path.name, relative, qualified_name=relative))
        edges.append(Edge(repo_id, file_id, EdgeKind.CONTAINS))
        if path.suffix != ".py":
            continue

        module = _module_name(relative, package_dirs)
        document = adapter.parse(path, relative, module)
        diagnostics.extend(document.diagnostics)
        if document.diagnostics:
            continue

        module_id = _id("module", f"{relative}:{module}")
        module_ids[module] = module_id
        nodes.append(Node(module_id, NodeKind.MODULE, module.rsplit(".", 1)[-1], relative, 1, module))
        edges.append(Edge(file_id, module_id, EdgeKind.DECLARES))
        documents.append((document, file_id))

        symbol_ids: dict[str, str] = {}
        for declaration in document.symbols:
            identity = (
                f"{relative}:{declaration.qualified_name}:{declaration.signature or ''}:"
                f"{declaration.line}"
            )
            node_id = _id(declaration.kind.value, identity)
            symbol_ids[declaration.qualified_name] = node_id
            declarations.append((declaration, node_id))
            nodes.append(
                Node(
                    node_id,
                    declaration.kind,
                    declaration.name,
                    relative,
                    declaration.line,
                    declaration.qualified_name,
                    declaration.signature,
                )
            )
            owner_id = symbol_ids.get(declaration.owner_qualified_name, module_id)
            edges.append(Edge(owner_id, node_id, EdgeKind.DECLARES))
            for base in declaration.bases:
                pending.append(PendingBase(node_id, base, document))

    catalog = SymbolCatalog(declarations)
    for document, file_id in documents:
        seen_modules: set[str] = set()
        for imported in document.imports:
            if imported.wildcard:
                diagnostics.append(
                    Diagnostic(
                        "unsupported_import",
                        f"wildcard import is not indexed: {imported.module}",
                        document.relative_path,
                        imported.line,
                    )
                )
                continue
            imported_module = imported.module
            if imported.name and f"{imported.module}.{imported.name}" in module_ids:
                imported_module = f"{imported.module}.{imported.name}"
            target = module_ids.get(imported_module)
            if target and imported_module not in seen_modules:
                edges.append(Edge(file_id, target, EdgeKind.IMPORTS))
                seen_modules.add(imported_module)
            elif target is None:
                diagnostics.append(
                    Diagnostic(
                        "unresolved_import",
                        f"unresolved import: {imported_module}",
                        document.relative_path,
                        imported.line,
                    )
                )

    for relation in pending:
        target, status = catalog.resolve(relation.expression, relation.document)
        if target:
            edges.append(Edge(relation.source, target, EdgeKind.EXTENDS))
        else:
            diagnostics.append(
                Diagnostic(
                    f"{status}_reference",
                    f"{status} reference: {relation.expression}",
                    relation.document.relative_path,
                )
            )

    return IndexResult(nodes, edges, diagnostics)
