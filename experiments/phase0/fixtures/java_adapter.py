from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from tree_sitter import Language, Node as SyntaxNode, Parser
import tree_sitter_java

from .models import Diagnostic, NodeKind

JAVA_LANGUAGE = Language(tree_sitter_java.language())
TYPE_NODES = {
    "class_declaration": NodeKind.CLASS,
    "interface_declaration": NodeKind.INTERFACE,
    "enum_declaration": NodeKind.ENUM,
    "record_declaration": NodeKind.RECORD,
}


@dataclass(frozen=True, slots=True)
class ImportDecl:
    qualified_name: str
    is_wildcard: bool
    is_static: bool


@dataclass(slots=True)
class TypeDecl:
    name: str
    qualified_name: str
    kind: NodeKind
    line: int
    relations: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class MemberDecl:
    owner_qualified_name: str
    name: str
    qualified_name: str
    signature: str
    kind: NodeKind
    line: int


@dataclass(slots=True)
class JavaDocument:
    path: Path
    package: str
    imports: list[ImportDecl]
    types: list[TypeDecl]
    members: list[MemberDecl]
    diagnostics: list[Diagnostic]


def _text(source: bytes, node: SyntaxNode | None) -> str:
    if node is None:
        return ""
    return source[node.start_byte : node.end_byte].decode("utf-8")


def _split_types(value: str) -> list[str]:
    result: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(value):
        if character == "<":
            depth += 1
        elif character == ">":
            depth = max(0, depth - 1)
        elif character == "," and depth == 0:
            result.append(value[start:index].strip())
            start = index + 1
    tail = value[start:].strip()
    if tail:
        result.append(tail)
    return result


def normalize_type(value: str) -> str:
    value = re.sub(r"@[\w$.]+(?:\([^)]*\))?\s*", "", value).strip()
    value = re.sub(r"\b(?:extends|implements|super|final)\b", "", value).strip()
    generic_depth = 0
    normalized: list[str] = []
    for character in value:
        if character == "<":
            generic_depth += 1
        elif character == ">":
            generic_depth = max(0, generic_depth - 1)
        elif generic_depth == 0 and not character.isspace():
            normalized.append(character)
    return "".join(normalized)


class JavaAdapter:
    def __init__(self) -> None:
        self.parser = Parser(JAVA_LANGUAGE)

    def parse(self, path: Path, relative_path: str) -> JavaDocument:
        try:
            source = path.read_bytes()
            source.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return JavaDocument(
                path,
                "",
                [],
                [],
                [],
                [Diagnostic("read_error", str(exc), relative_path)],
            )

        tree = self.parser.parse(source)
        if tree.root_node.has_error:
            return JavaDocument(
                path,
                "",
                [],
                [],
                [],
                [Diagnostic("syntax_error", "Java syntax tree contains errors", relative_path)],
            )

        package = ""
        imports: list[ImportDecl] = []
        for child in tree.root_node.named_children:
            if child.type == "package_declaration":
                package = _text(source, child).removeprefix("package").removesuffix(";").strip()
            elif child.type == "import_declaration":
                declaration = _text(source, child).removeprefix("import").removesuffix(";").strip()
                is_static = declaration.startswith("static ")
                if is_static:
                    declaration = declaration.removeprefix("static ").strip()
                is_wildcard = declaration.endswith(".*")
                imports.append(ImportDecl(declaration.removesuffix(".*"), is_wildcard, is_static))

        types: list[TypeDecl] = []
        members: list[MemberDecl] = []
        self._walk_declarations(tree.root_node, source, package, (), types, members)
        return JavaDocument(path, package, imports, types, members, [])

    def _walk_declarations(
        self,
        node: SyntaxNode,
        source: bytes,
        package: str,
        enclosing: tuple[str, ...],
        types: list[TypeDecl],
        members: list[MemberDecl],
    ) -> None:
        if node.type in TYPE_NODES:
            name = _text(source, node.child_by_field_name("name"))
            qualified_parts = tuple(part for part in (package, *enclosing, name) if part)
            qualified_name = ".".join(qualified_parts)
            declaration = TypeDecl(
                name=name,
                qualified_name=qualified_name,
                kind=TYPE_NODES[node.type],
                line=node.start_point.row + 1,
                relations=self._type_relations(node, source),
            )
            types.append(declaration)
            body = node.child_by_field_name("body")
            if body is not None:
                for child in body.named_children:
                    self._walk_declarations(
                        child,
                        source,
                        package,
                        (*enclosing, name),
                        types,
                        members,
                    )
            return

        if enclosing and node.type in {"method_declaration", "constructor_declaration"}:
            owner_parts = tuple(part for part in (package, *enclosing) if part)
            owner = ".".join(owner_parts)
            raw_name = _text(source, node.child_by_field_name("name"))
            kind = NodeKind.CONSTRUCTOR if node.type == "constructor_declaration" else NodeKind.METHOD
            name = "<init>" if kind == NodeKind.CONSTRUCTOR else raw_name
            signature = self._signature(node, source)
            members.append(
                MemberDecl(
                    owner_qualified_name=owner,
                    name=raw_name,
                    qualified_name=f"{owner}#{name}{signature}",
                    signature=signature,
                    kind=kind,
                    line=node.start_point.row + 1,
                )
            )

        for child in node.named_children:
            self._walk_declarations(child, source, package, enclosing, types, members)

    @staticmethod
    def _signature(node: SyntaxNode, source: bytes) -> str:
        parameters = node.child_by_field_name("parameters")
        if parameters is None:
            return "()"
        parameter_types: list[str] = []
        for parameter in parameters.named_children:
            type_node = parameter.child_by_field_name("type")
            if type_node is None and parameter.type == "spread_parameter":
                type_node = next((child for child in parameter.named_children if "type" in child.type), None)
            value = normalize_type(_text(source, type_node))
            if parameter.type == "spread_parameter":
                value += "..."
            if value:
                parameter_types.append(value)
        return f"({','.join(parameter_types)})"

    @staticmethod
    def _type_relations(node: SyntaxNode, source: bytes) -> list[tuple[str, str]]:
        relations: list[tuple[str, str]] = []
        wrappers = {
            "superclass": "extends",
            "super_interfaces": "implements",
            "extends_interfaces": "extends",
        }
        for child in node.named_children:
            relation = wrappers.get(child.type)
            if relation is None:
                continue
            value = _text(source, child)
            value = re.sub(r"^(?:extends|implements)\s+", "", value).strip()
            for raw_type in _split_types(value):
                normalized = normalize_type(raw_type)
                if normalized:
                    relations.append((relation, normalized))
        return relations
