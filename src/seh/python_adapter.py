from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .models import Diagnostic, NodeKind


@dataclass(frozen=True, slots=True)
class ImportDecl:
    module: str
    name: str | None
    alias: str
    wildcard: bool
    line: int


@dataclass(frozen=True, slots=True)
class SymbolDecl:
    name: str
    qualified_name: str
    kind: NodeKind
    line: int
    signature: str | None
    owner_qualified_name: str
    bases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PythonDocument:
    path: Path
    relative_path: str
    module: str
    imports: tuple[ImportDecl, ...]
    symbols: tuple[SymbolDecl, ...]
    diagnostics: tuple[Diagnostic, ...]


def _expression_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = _expression_name(node.value)
        return f"{owner}.{node.attr}" if owner else None
    if isinstance(node, ast.Subscript):
        return _expression_name(node.value)
    return None


def _absolute_import(
    module: str,
    imported: str | None,
    level: int,
    *,
    is_package: bool,
) -> str:
    if level == 0:
        return imported or ""
    package = module if is_package else module.rpartition(".")[0]
    parts = package.split(".") if package else []
    keep = max(0, len(parts) - (level - 1))
    prefix = parts[:keep]
    if imported:
        prefix.extend(imported.split("."))
    return ".".join(prefix)


class PythonAdapter:
    def parse(self, path: Path, relative_path: str, module: str) -> PythonDocument:
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            return PythonDocument(
                path,
                relative_path,
                module,
                (),
                (),
                (Diagnostic("read_error", f"unable to read source: {exc}", relative_path),),
            )

        try:
            tree = ast.parse(source, filename=relative_path)
        except SyntaxError as exc:
            return PythonDocument(
                path,
                relative_path,
                module,
                (),
                (),
                (
                    Diagnostic(
                        "syntax_error",
                        exc.msg,
                        relative_path,
                        exc.lineno,
                    ),
                ),
            )

        imports: list[ImportDecl] = []
        symbols: list[SymbolDecl] = []

        for statement in tree.body:
            if isinstance(statement, ast.Import):
                for item in statement.names:
                    imports.append(
                        ImportDecl(
                            item.name,
                            None,
                            item.asname or item.name.split(".")[0],
                            False,
                            statement.lineno,
                        )
                    )
            elif isinstance(statement, ast.ImportFrom):
                imported_module = _absolute_import(
                    module,
                    statement.module,
                    statement.level,
                    is_package=path.name == "__init__.py",
                )
                for item in statement.names:
                    imports.append(
                        ImportDecl(
                            imported_module,
                            None if item.name == "*" else item.name,
                            item.asname or item.name,
                            item.name == "*",
                            statement.lineno,
                        )
                    )

        def visit_body(body: list[ast.stmt], owner: str, *, inside_class: bool) -> None:
            for statement in body:
                qualified = f"{owner}.{getattr(statement, 'name', '')}"
                if isinstance(statement, ast.ClassDef):
                    bases = tuple(
                        name
                        for base in statement.bases
                        if (name := _expression_name(base)) is not None
                    )
                    symbols.append(
                        SymbolDecl(
                            statement.name,
                            qualified,
                            NodeKind.CLASS,
                            statement.lineno,
                            None,
                            owner,
                            bases,
                        )
                    )
                    visit_body(statement.body, qualified, inside_class=True)
                elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = ast.get_source_segment(source, statement.args) or ast.unparse(statement.args)
                    returns = (
                        ast.get_source_segment(source, statement.returns)
                        if statement.returns is not None
                        else None
                    )
                    signature = f"({args})" + (f" -> {returns}" if returns else "")
                    symbols.append(
                        SymbolDecl(
                            statement.name,
                            qualified,
                            NodeKind.METHOD if inside_class else NodeKind.FUNCTION,
                            statement.lineno,
                            signature,
                            owner,
                        )
                    )

        visit_body(tree.body, module, inside_class=False)
        return PythonDocument(
            path,
            relative_path,
            module,
            tuple(imports),
            tuple(symbols),
            (),
        )
