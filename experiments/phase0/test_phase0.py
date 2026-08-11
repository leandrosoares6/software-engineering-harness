"""Phase 0 evidence, as executable assertions.

Run explicitly — this is not part of the product suite:

    pytest experiments/phase0

Each test corresponds to a finding in `docs/PHASE0_FINDINGS.md`. The negative
findings are asserted too: F9 is encoded as a test that *requires* the failure,
so the reason Phase 0 is still open cannot silently stop being true.
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import importlib
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from capabilities import (  # noqa: E402
    WRAPPERS,
    add_cli_command,
    add_java_relation_kind,
    add_node_kind,
)
from primitives import AnchorNotFound, locate_collection_literal  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[2]


def fixture(name: str) -> bytes:
    return (FIXTURES / f"{name}.py").read_bytes()


def pre_existing_lines_kept(before: bytes, after: bytes) -> int:
    """How many original lines survive byte-identically."""
    old = before.decode().splitlines()
    new = after.decode().splitlines()
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    removed = sum(i2 - i1 for tag, i1, i2, _, _ in matcher.get_opcodes() if tag != "equal")
    return len(old) - removed


# --- provenance -----------------------------------------------------------


def test_fixtures_match_their_recorded_baseline():
    """A fixture is only evidence if it is the bytes it claims to be."""
    recorded = {
        line.split()[1]: line.split()[2]
        for line in (FIXTURES / "BASELINE").read_text().splitlines()
        if line.startswith("sha256")
    }
    assert recorded, "BASELINE records no hashes"
    for name, expected in recorded.items():
        actual = hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest()
        assert actual == expected, f"{name} does not match its recorded baseline"


# --- F1: source preservation ---------------------------------------------


@pytest.mark.parametrize("name", ["report", "doctor"])
def test_cli_capability_is_insert_only(name):
    before = fixture("cli")
    after = add_cli_command(before, name=name)
    assert pre_existing_lines_kept(before, after) == len(before.decode().splitlines())
    assert len(after) > len(before)


def test_node_kind_capability_is_insert_only():
    models, adapter = fixture("models"), fixture("java_adapter")
    new_models, new_adapter = add_node_kind(
        models,
        adapter,
        name="ANNOTATION",
        value="annotation",
        java_node="annotation_type_declaration",
    )
    for before, after in ((models, new_models), (adapter, new_adapter)):
        assert pre_existing_lines_kept(before, after) == len(before.decode().splitlines())


def test_comments_survive_the_edit():
    """The reason ast.unparse() is banned from the mutation path."""
    adapter = fixture("java_adapter")
    _, patched = add_node_kind(
        fixture("models"),
        adapter,
        name="ANNOTATION",
        value="annotation",
        java_node="annotation_type_declaration",
    )
    comments = [
        line for line in adapter.decode().splitlines() if line.strip().startswith("#")
    ]
    for comment in comments:
        assert comment in patched.decode(), f"comment lost: {comment!r}"


# --- F2: the scaffolding actually runs ------------------------------------


def _seh_modules() -> list[str]:
    return [name for name in sys.modules if name == "seh" or name.startswith("seh.")]


def test_generated_command_imports_and_dispatches(tmp_path):
    patched = add_cli_command(fixture("cli"), name="report")

    package = tmp_path / "seh"
    shutil.copytree(REPO / "src/seh", package)
    (package / "cli.py").write_bytes(patched)

    # Importing a second copy of `seh` requires evicting the real one. Save the
    # original module objects and put them back afterwards: merely deleting them
    # would leave any already-imported binding (e.g. a product test's top-level
    # `from seh.cli import cmd_index`) pointing at a module that monkeypatch can
    # no longer reach.
    saved = {name: sys.modules[name] for name in _seh_modules()}
    sys.path.insert(0, str(tmp_path))
    try:
        for name in list(saved):
            del sys.modules[name]
        cli = importlib.import_module("seh.cli")
        parsed = cli.build_parser().parse_args(["report"])
        assert parsed.handler.__name__ == "cmd_report"
        with pytest.raises(NotImplementedError):
            parsed.handler(parsed)
        existing = cli.build_parser().parse_args(["inspect", "X"])
        assert existing.handler.__name__ == "cmd_inspect"
    finally:
        sys.path.remove(str(tmp_path))
        for name in _seh_modules():
            del sys.modules[name]
        sys.modules.update(saved)


# --- F3: idempotency and safe refusal -------------------------------------


def test_cli_capability_refuses_second_application():
    once = add_cli_command(fixture("cli"), name="report")
    with pytest.raises(AnchorNotFound, match="already exists"):
        add_cli_command(once, name="report")


def test_relation_capability_refuses_second_application():
    models, adapter = add_java_relation_kind(
        fixture("models"),
        fixture("java_adapter"),
        name="OVERRIDES",
        value="overrides",
        syntax_nodes=["overrides_clause"],
    )
    with pytest.raises(AnchorNotFound, match="already exists"):
        add_java_relation_kind(
            models,
            adapter,
            name="OVERRIDES",
            value="overrides",
            syntax_nodes=["overrides_clause"],
        )


def test_refuses_missing_anchor():
    with pytest.raises(AnchorNotFound, match="no module-level function"):
        add_cli_command(b"x = 1\n", name="report")


def test_refuses_wrong_syntactic_form():
    """A dict() call is a different form from a dict literal, and is not adapted."""
    source = b"class JavaAdapter:\n    def _type_relations(self):\n        wrappers = dict(a=1)\n"
    with pytest.raises(AnchorNotFound, match="not a dict/list/set literal"):
        locate_collection_literal(source, WRAPPERS)


def test_refuses_missing_scope():
    with pytest.raises(AnchorNotFound, match="scope 'JavaAdapter' not found"):
        locate_collection_literal(b"x = 1\n", WRAPPERS)


# --- F4/F5: style is derived, not imposed ---------------------------------


def test_enum_member_uses_sibling_rhythm_not_enclosing_gap():
    """Regression for F4: the gap after a last child belongs to the outer scope."""
    models, _ = add_node_kind(
        fixture("models"),
        fixture("java_adapter"),
        name="ANNOTATION",
        value="annotation",
        java_node="annotation_type_declaration",
    )
    assert '    TEST = "test"\n    ANNOTATION = "annotation"' in models.decode(), (
        "an enum member must follow its sibling directly, with no blank lines"
    )


def test_collection_entry_inherits_trailing_comma_style():
    _, adapter = add_node_kind(
        fixture("models"),
        fixture("java_adapter"),
        name="ANNOTATION",
        value="annotation",
        java_node="annotation_type_declaration",
    )
    assert '    "annotation_type_declaration": NodeKind.ANNOTATION,\n}' in adapter.decode()


# --- F7: primitive reuse across shapes ------------------------------------


def test_same_locator_reaches_a_method_local_collection():
    """The discriminating result: scope addressing, not a new primitive."""
    span = locate_collection_literal(fixture("java_adapter"), WRAPPERS)
    assert span.kind == "python.collection_literal"
    assert span.label == WRAPPERS


def test_relation_capability_handles_variable_cardinality():
    """EXTENDS maps two syntax nodes, IMPLEMENTS maps one."""
    models, adapter = fixture("models"), fixture("java_adapter")
    _, two = add_java_relation_kind(
        models,
        adapter,
        name="OVERRIDES",
        value="overrides",
        syntax_nodes=["overrides_clause", "override_annotation"],
    )
    _, one = add_java_relation_kind(
        models, adapter, name="SEALS", value="seals", syntax_nodes=["permits_clause"]
    )
    assert two.decode().count('"overrides"') == 2
    assert one.decode().count('"seals"') == 1


# --- F9: the negative finding, asserted -----------------------------------


def test_fixture_built_by_subtraction_fails_fidelity():
    """Phase 0 stays open because of this.

    Deleting EXTENDS from the current snapshot produces a state that never
    existed: member order records the order in which things were historically
    added, so an append-style capability cannot reproduce the accepted ordering.
    If this test ever starts failing, a fixture is being reconstructed rather
    than captured.
    """
    accepted_models = fixture("models")
    accepted_adapter = fixture("java_adapter")

    synthetic_models = accepted_models.replace(b'    EXTENDS = "extends"\n', b"")
    synthetic_adapter = accepted_adapter.replace(
        b'            "superclass": "extends",\n', b""
    ).replace(b'            "extends_interfaces": "extends",\n', b"")
    assert synthetic_models != accepted_models

    replayed_models, replayed_adapter = add_java_relation_kind(
        synthetic_models,
        synthetic_adapter,
        name="EXTENDS",
        value="extends",
        syntax_nodes=["superclass", "extends_interfaces"],
    )

    assert replayed_models != accepted_models, "subtraction fixture unexpectedly reproduced order"
    assert replayed_adapter != accepted_adapter
    # ...yet the result is still valid Python: wrong order, not broken code.
    ast.parse(replayed_models)
    ast.parse(replayed_adapter)
