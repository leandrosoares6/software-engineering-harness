"""Phase 0 prototype: the provisional primitive algebra.

NOT part of the SEH runtime. Nothing under `src/` imports this module. It exists
to make the Phase 0 evidence reproducible, and is frozen alongside the findings
it supports.

The contract it demonstrates:

    Python AST  -> locate and validate a structural anchor -> exact byte offset
    source text -> splice a rendered fragment at that offset -> patch

`ast.unparse()` is never used. A parse/unparse round trip rewrites source even
when the tree is untouched: comments vanish, quote style and blank lines change.
Locating with the AST and writing with a text splice keeps every byte outside the
declared fragment identical.

Everything works on `bytes` because `ast` reports `col_offset` as a UTF-8 byte
offset within its line.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    """A validated structural anchor, as absolute byte offsets.

    `separator` is the vertical rhythm between siblings of this anchor's parent,
    measured from existing source. It belongs to the locator, not to the effect:
    only the locator knows what the anchor's siblings are. Measuring the raw
    whitespace that follows the anchor is wrong for a last child, because that
    gap belongs to the enclosing scope rather than to the sibling sequence.
    """

    start: int
    end: int
    kind: str
    label: str
    separator: bytes = b"\n"

    def start_column(self, source: bytes) -> int:
        """Indentation of the anchor's own line, derived from the source."""
        line_start = source.rfind(b"\n", 0, self.start) + 1
        return self.start - line_start


class AnchorNotFound(Exception):
    """Raised when a declared anchor is absent or of the wrong kind.

    This is gate 4 (safe refusal): never adapt, never guess.
    """


def _line_starts(source: bytes) -> list[int]:
    starts = [0]
    for index, byte in enumerate(source):
        if byte == 0x0A:
            starts.append(index + 1)
    return starts


def _offset(source: bytes, lineno: int, col: int) -> int:
    return _line_starts(source)[lineno - 1] + col


def _sibling_separator(source: bytes, siblings: list[ast.stmt]) -> bytes:
    """Measure the vertical rhythm between two existing siblings.

    Falls back to a single newline when the parent has only one child: there is
    no rhythm to observe, and inventing one would impose a style.
    """
    if len(siblings) < 2:
        return b"\n"
    previous, current = siblings[-2], siblings[-1]
    gap_start = _offset(source, previous.end_lineno, previous.end_col_offset)
    gap_end = _offset(source, current.lineno, current.col_offset)
    return b"\n" * source[gap_start:gap_end].count(b"\n") or b"\n"


def _span(
    source: bytes,
    node: ast.AST,
    kind: str,
    label: str,
    siblings: list[ast.stmt] | None = None,
) -> Span:
    return Span(
        start=_offset(source, node.lineno, node.col_offset),
        end=_offset(source, node.end_lineno, node.end_col_offset),
        kind=kind,
        label=label,
        separator=_sibling_separator(source, siblings) if siblings else b"\n",
    )


# --- LOCATORS -------------------------------------------------------------


def locate_last_function_with_prefix(source: bytes, prefix: str) -> Span:
    """python.symbol — the last module-level function whose name starts with prefix."""
    body = ast.parse(source).body
    found = [
        node
        for node in body
        if isinstance(node, ast.FunctionDef) and node.name.startswith(prefix)
    ]
    if not found:
        raise AnchorNotFound(f"no module-level function starting with {prefix!r}")
    functions = [node for node in body if isinstance(node, ast.FunctionDef)]
    return _span(source, found[-1], "python.symbol", f"def {found[-1].name}", functions)


def locate_return_in_function(source: bytes, function: str) -> Span:
    """python.statement — the top-level return statement of a named function."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name == function:
            for statement in node.body:
                if isinstance(statement, ast.Return):
                    return _span(source, statement, "python.statement", f"return in {function}")
            raise AnchorNotFound(f"function {function!r} has no top-level return")
    raise AnchorNotFound(f"no module-level function named {function!r}")


def locate_class_body_tail(source: bytes, class_name: str) -> Span:
    """python.class_body — the last statement of a class body."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return _span(
                source, node.body[-1], "python.class_body", f"class {class_name}", node.body
            )
    raise AnchorNotFound(f"no class named {class_name!r}")


def _resolve_scope(source: bytes, path: str) -> tuple[list[ast.stmt], str]:
    """Walk a dotted scope path down to the body that should contain the target.

        'TYPE_NODES'                           -> module body
        'JavaAdapter._type_relations.wrappers' -> that method's body

    Addressing by scope path is what lets one locator serve a module-level
    constant and a method-local binding instead of needing two primitives.
    """
    *scopes, name = path.split(".")
    body = ast.parse(source).body
    for scope in scopes:
        for node in body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == scope:
                body = node.body
                break
        else:
            raise AnchorNotFound(f"scope {scope!r} not found while resolving {path!r}")
    return body, name


def locate_collection_literal(source: bytes, path: str) -> Span:
    """python.collection_literal — a dict/list/set literal bound by assignment.

    Declares one syntactic form and refuses every other. A `.extend()` call, a
    decorator registry and an annotation-based registry are different forms that
    require different support or explicit refusal.
    """
    body, name = _resolve_scope(source, path)
    for node in body:
        if not isinstance(node, ast.Assign):
            continue
        if name not in [t.id for t in node.targets if isinstance(t, ast.Name)]:
            continue
        if not isinstance(node.value, (ast.Dict, ast.List, ast.Set)):
            raise AnchorNotFound(
                f"{path!r} is not a dict/list/set literal "
                f"(got {type(node.value).__name__}); this primitive refuses it"
            )
        return _span(source, node.value, "python.collection_literal", path)
    raise AnchorNotFound(f"no assignment named {name!r} in scope {path!r}")


# --- EFFECTS --------------------------------------------------------------


def splice_after(source: bytes, span: Span, fragment: bytes) -> bytes:
    """Insert after an AST sibling, reproducing that sibling sequence's rhythm.

    `fragment` carries no leading or trailing newlines: the separator comes from
    `span.separator`, measured by the locator between two real siblings.
    """
    indent = b" " * span.start_column(source)
    body = b"\n".join(indent + line if line else b"" for line in fragment.split(b"\n"))
    return source[: span.end] + span.separator + body + source[span.end :]


def splice_before(source: bytes, span: Span, fragment: bytes, *, lead: bytes = b"") -> bytes:
    """Insert before a span's own line, indenting to match that line.

    Indentation *is* derived. The vertical `lead` is not: the unit being inserted
    — an argparse registration block, for instance — is a *conventional* group of
    statements rather than a single AST node, so the tree exposes no sibling
    boundary to measure. The capability must declare it.

    Finding F5: AST-derived style covers horizontal rhythm and sibling-level
    vertical rhythm, but not groupings the grammar does not model.
    """
    line_start = source.rfind(b"\n", 0, span.start) + 1
    indent_end = line_start
    while source[indent_end : indent_end + 1] in (b" ", b"\t"):
        indent_end += 1
    indent = source[line_start:indent_end]

    body = b"\n".join(indent + line if line else b"" for line in fragment.split(b"\n"))
    return source[:line_start] + lead + body + b"\n" + source[line_start:]


def splice_into_collection(source: bytes, span: Span, entry: bytes) -> bytes:
    """Append an entry to a collection literal, deriving style from its neighbours.

    Indentation and the trailing-comma convention are read from existing source,
    never imposed: SEH must not require a particular formatter.
    """
    body = source[span.start : span.end]
    inner = body[1:-1]
    stripped = inner.rstrip()
    if not stripped:
        raise AnchorNotFound("empty collection: no neighbouring style to derive from")

    trailing_comma = stripped.endswith(b",")
    tail = inner[len(stripped) :]
    last_line = stripped[stripped.rfind(b"\n") + 1 :]
    indent = last_line[: len(last_line) - len(last_line.lstrip())]

    if b"\n" in inner:
        separator = b"" if trailing_comma else b","
        addition = separator + b"\n" + indent + entry + (b"," if trailing_comma else b"")
    else:
        addition = b", " + entry

    return (
        source[: span.start]
        + body[0:1]
        + stripped
        + addition
        + tail
        + body[-1:]
        + source[span.end :]
    )
