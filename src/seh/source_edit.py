from __future__ import annotations

import ast
from dataclasses import dataclass

from .errors import CapabilityRefusal


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    separator: bytes = b"\n"

    def start_column(self, source: bytes) -> int:
        return self.start - (source.rfind(b"\n", 0, self.start) + 1)


def _line_starts(source: bytes) -> list[int]:
    starts = [0]
    starts.extend(index + 1 for index, byte in enumerate(source) if byte == 0x0A)
    return starts


def _offset(source: bytes, lineno: int, column: int) -> int:
    return _line_starts(source)[lineno - 1] + column


def _module(source: bytes) -> ast.Module:
    try:
        return ast.parse(source)
    except (SyntaxError, UnicodeDecodeError) as exc:
        raise CapabilityRefusal(f"source is not valid UTF-8 Python: {exc}") from exc


def _sibling_separator(source: bytes, siblings: list[ast.stmt]) -> bytes:
    if len(siblings) < 2:
        return b"\n"
    previous, current = siblings[-2], siblings[-1]
    start = _offset(source, previous.end_lineno, previous.end_col_offset)
    end = _offset(source, current.lineno, current.col_offset)
    return b"\n" * source[start:end].count(b"\n") or b"\n"


def locate_last_function_with_prefix(source: bytes, prefix: str) -> Span:
    functions = [
        node for node in _module(source).body if isinstance(node, ast.FunctionDef)
    ]
    matches = [node for node in functions if node.name.startswith(prefix)]
    if not matches:
        raise CapabilityRefusal(f"no module-level function starting with {prefix!r}")
    node = matches[-1]
    return Span(
        start=_offset(source, node.lineno, node.col_offset),
        end=_offset(source, node.end_lineno, node.end_col_offset),
        separator=_sibling_separator(source, functions),
    )


def locate_return_in_function(source: bytes, function: str) -> Span:
    for node in _module(source).body:
        if isinstance(node, ast.FunctionDef) and node.name == function:
            for statement in node.body:
                if isinstance(statement, ast.Return):
                    return Span(
                        start=_offset(source, statement.lineno, statement.col_offset),
                        end=_offset(
                            source, statement.end_lineno, statement.end_col_offset
                        ),
                    )
            raise CapabilityRefusal(f"function {function!r} has no top-level return")
    raise CapabilityRefusal(f"no module-level function named {function!r}")


def splice_after(source: bytes, span: Span, fragment: bytes) -> bytes:
    indent = b" " * span.start_column(source)
    body = b"\n".join(indent + line if line else b"" for line in fragment.split(b"\n"))
    return source[: span.end] + span.separator + body + source[span.end :]


def splice_before(
    source: bytes, span: Span, fragment: bytes, *, lead: bytes = b""
) -> bytes:
    line_start = source.rfind(b"\n", 0, span.start) + 1
    indent_end = line_start
    while source[indent_end : indent_end + 1] in (b" ", b"\t"):
        indent_end += 1
    indent = source[line_start:indent_end]
    body = b"\n".join(indent + line if line else b"" for line in fragment.split(b"\n"))
    return source[:line_start] + lead + body + b"\n" + source[line_start:]
