from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .git import repository_root, tracked_files
from .java_adapter import ImportDecl, JavaAdapter, JavaDocument, TypeDecl, normalize_type
from .models import Diagnostic, Edge, EdgeKind, IndexResult, Node, NodeKind


def _id(kind: str, value: str) -> str:
    digest = hashlib.sha256(f"{kind}:{value}".encode()).hexdigest()[:20]
    return f"{kind}:{digest}"


def _is_test(path: Path) -> bool:
    normalized = path.as_posix().lower()
    return "/test/" in normalized or path.stem.endswith(("Test", "Tests", "IT"))


@dataclass(frozen=True, slots=True)
class PendingRelation:
    source: str
    kind: EdgeKind
    target_name: str
    document: JavaDocument
    enclosing_type: str | None = None


class TypeCatalog:
    def __init__(self, declarations: list[tuple[TypeDecl, str]]) -> None:
        self.by_qualified: dict[str, list[str]] = defaultdict(list)
        for declaration, node_id in declarations:
            self.by_qualified[declaration.qualified_name].append(node_id)

    def resolve(
        self,
        raw_name: str,
        document: JavaDocument,
        enclosing_type: str | None,
    ) -> tuple[str | None, str]:
        name = normalize_type(raw_name)
        levels: list[list[str]] = []
        levels.append([name])

        if enclosing_type:
            owner = enclosing_type
            while owner and owner != document.package:
                levels.append([f"{owner}.{name}"])
                if "." not in owner:
                    break
                owner = owner.rsplit(".", 1)[0]

        first_component = name.split(".", 1)[0]
        explicit = [
            item.qualified_name + name[len(first_component) :]
            for item in document.imports
            if not item.is_wildcard
            and not item.is_static
            and item.qualified_name.rsplit(".", 1)[-1] == first_component
        ]
        if explicit:
            levels.append(explicit)
        levels.append([f"{document.package}.{name}" if document.package else name])
        levels.append([f"java.lang.{name}"])
        wildcard = [
            f"{item.qualified_name}.{name}"
            for item in document.imports
            if item.is_wildcard and not item.is_static
        ]
        if wildcard:
            levels.append(wildcard)

        seen: set[str] = set()
        for candidates in levels:
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
    nodes: list[Node] = []
    edges: list[Edge] = []
    diagnostics: list[Diagnostic] = []

    repo_id = _id("repository", str(root))
    nodes.append(Node(repo_id, NodeKind.REPOSITORY, root.name, str(root), qualified_name=str(root)))

    adapter = JavaAdapter()
    documents: list[tuple[JavaDocument, str, str]] = []
    declarations: list[tuple[TypeDecl, str]] = []
    pending: list[PendingRelation] = []

    for path in (item for item in tracked_files(root) if item.is_file()):
        relative = path.relative_to(root).as_posix()
        file_id = _id("file", relative)
        file_kind = NodeKind.TEST if _is_test(path) else NodeKind.FILE
        nodes.append(Node(file_id, file_kind, path.name, relative, qualified_name=relative))
        edges.append(Edge(repo_id, file_id, EdgeKind.CONTAINS))
        if path.suffix != ".java":
            continue

        document = adapter.parse(path, relative)
        diagnostics.extend(document.diagnostics)
        documents.append((document, relative, file_id))
        type_ids: dict[str, str] = {}
        for declaration in document.types:
            type_id = _id(declaration.kind.value, f"{relative}:{declaration.qualified_name}")
            type_ids[declaration.qualified_name] = type_id
            declarations.append((declaration, type_id))
            nodes.append(
                Node(
                    type_id,
                    declaration.kind,
                    declaration.name,
                    relative,
                    declaration.line,
                    declaration.qualified_name,
                )
            )
            parent_name = declaration.qualified_name.rsplit(".", 1)[0]
            parent_id = type_ids.get(parent_name, file_id)
            edges.append(Edge(parent_id, type_id, EdgeKind.DECLARES))
            for relation_name, target_name in declaration.relations:
                pending.append(
                    PendingRelation(
                        type_id,
                        EdgeKind(relation_name),
                        target_name,
                        document,
                        declaration.qualified_name,
                    )
                )

        for member in document.members:
            owner_id = type_ids.get(member.owner_qualified_name)
            if owner_id is None:
                continue
            member_id = _id(member.kind.value, f"{relative}:{member.qualified_name}")
            nodes.append(
                Node(
                    member_id,
                    member.kind,
                    member.name,
                    relative,
                    member.line,
                    member.qualified_name,
                    member.signature,
                )
            )
            edges.append(Edge(owner_id, member_id, EdgeKind.CONTAINS))

    catalog = TypeCatalog(declarations)
    for document, relative, file_id in documents:
        for imported in document.imports:
            if imported.is_static:
                diagnostics.append(
                    Diagnostic(
                        "unsupported_import",
                        f"static import is not indexed: {imported.qualified_name}",
                        relative,
                    )
                )
                continue
            if imported.is_wildcard:
                continue
            target, status = catalog.resolve(imported.qualified_name, document, None)
            if target:
                edges.append(Edge(file_id, target, EdgeKind.IMPORTS))
            else:
                diagnostics.append(
                    Diagnostic(
                        f"{status}_import",
                        f"{status} import: {imported.qualified_name}",
                        relative,
                    )
                )

    for relation in pending:
        target, status = catalog.resolve(
            relation.target_name,
            relation.document,
            relation.enclosing_type,
        )
        if target:
            edges.append(Edge(relation.source, target, relation.kind))
        else:
            diagnostics.append(
                Diagnostic(
                    f"{status}_reference",
                    f"{status} reference: {relation.target_name}",
                    relation.document.path.relative_to(root).as_posix(),
                )
            )

    return IndexResult(nodes, edges, diagnostics)
