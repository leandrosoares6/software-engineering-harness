"""Phase 0 prototype: three hand-authored capabilities.

NOT part of the SEH runtime. These are written by hand, in Python, precisely
because Phase 0 must not presuppose a manifest schema or a CLI. What matters here
is which primitives each one needs, not how it is declared.

Each capability composes only primitives from `primitives.py`, is closed (every
variation is a typed parameter, never a code slot), and scaffolds structure
without authoring domain behaviour.
"""

from __future__ import annotations

from primitives import (
    AnchorNotFound,
    locate_class_body_tail,
    locate_collection_literal,
    locate_last_function_with_prefix,
    locate_return_in_function,
    splice_after,
    splice_before,
    splice_into_collection,
)

WRAPPERS = "JavaAdapter._type_relations.wrappers"

HANDLER = '''def cmd_{name}(args: argparse.Namespace) -> int:
    raise NotImplementedError("cmd_{name}")'''

REGISTRATION = '''{name}_command = subcommands.add_parser("{name}")
{name}_command.add_argument("--repo")
{name}_command.set_defaults(handler=cmd_{name})'''


def add_cli_command(source: bytes, *, name: str) -> bytes:
    """Add a top-level CLI subcommand to `cli.py`.

    Scaffolding only. The handler body is domain logic and stays manual work; the
    skeleton fails loudly so an unimplemented command cannot pass silently
    (finding F6).

    Primitives: python.symbol, python.statement, splice.after, splice.before.
    """
    if f"def cmd_{name}(".encode() in source:
        raise AnchorNotFound(f"cmd_{name} already exists (idempotency refusal)")

    anchor = locate_last_function_with_prefix(source, "cmd_")
    source = splice_after(source, anchor, HANDLER.format(name=name).encode())

    anchor = locate_return_in_function(source, "build_parser")
    return splice_before(source, anchor, REGISTRATION.format(name=name).encode(), lead=b"\n")


def add_node_kind(
    models: bytes, adapter: bytes, *, name: str, value: str, java_node: str
) -> tuple[bytes, bytes]:
    """Add a NodeKind member and its Java syntax-node mapping.

    Primitives: python.class_body, python.collection_literal, splice.after,
    splice.into_collection.
    """
    if f"    {name} = ".encode() in models:
        raise AnchorNotFound(f"NodeKind.{name} already exists (idempotency refusal)")

    anchor = locate_class_body_tail(models, "NodeKind")
    models = splice_after(models, anchor, f'{name} = "{value}"'.encode())

    anchor = locate_collection_literal(adapter, "TYPE_NODES")
    adapter = splice_into_collection(adapter, anchor, f'"{java_node}": NodeKind.{name}'.encode())
    return models, adapter


def add_java_relation_kind(
    models: bytes, adapter: bytes, *, name: str, value: str, syntax_nodes: list[str]
) -> tuple[bytes, bytes]:
    """Add an EdgeKind member and its syntax-node mappings.

    Shape-adjacent to `add_node_kind`, but the target collection is local to a
    method rather than module-level. It reuses the same four primitives, which is
    the evidence that scope addressing is a locator refinement and not a new
    primitive (finding F7).

    `syntax_nodes` is a list, not a scalar: EXTENDS maps two Java syntax nodes
    while IMPLEMENTS maps one. A capability hard-coded to a single entry would
    pass one case and fail the other.
    """
    if f"    {name} = ".encode() in models:
        raise AnchorNotFound(f"EdgeKind.{name} already exists (idempotency refusal)")

    anchor = locate_class_body_tail(models, "EdgeKind")
    models = splice_after(models, anchor, f'{name} = "{value}"'.encode())

    for syntax_node in syntax_nodes:
        if f'"{syntax_node}"'.encode() in adapter:
            raise AnchorNotFound(f"{syntax_node!r} already mapped (idempotency refusal)")
        anchor = locate_collection_literal(adapter, WRAPPERS)
        adapter = splice_into_collection(adapter, anchor, f'"{syntax_node}": "{value}"'.encode())
    return models, adapter
