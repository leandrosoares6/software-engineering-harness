"""Direct tests for the source-preserving edit primitives.

These exist because the guarantee they pin — inserted text adopts the rhythm of
the *siblings of the same structural parent* — was previously proved only by a
Phase 0 experiment built on the Java adapter. That adapter was removed in the
Python-only migration and took the proof with it, while
`docs/CAPABILITY_MODEL.md` still asserts the rule. It is pinned here instead,
against the product implementation.

Only the two admitted locators and two admitted effects are covered, because
that is the whole algebra.
"""

from __future__ import annotations

import ast

import pytest

from seh.errors import CapabilityRefusal
from seh.source_edit import (
    locate_last_function_with_prefix,
    locate_return_in_function,
    splice_after,
    splice_before,
)

MODULE = b'''from __future__ import annotations


def cmd_first() -> int:
    return 0


def cmd_second() -> int:
    return 0


def build_parser() -> object:
    parser = object()
    return parser
'''


def test_insertion_adopts_the_rhythm_between_function_siblings():
    span = locate_last_function_with_prefix(MODULE, "cmd_")
    result = splice_after(MODULE, span, b"def cmd_third() -> int:\n    return 0")

    assert b"    return 0\n\n\ndef cmd_third() -> int:" in result
    assert b"    return 0\n\n\ndef build_parser" in result
    ast.parse(result)


def test_separator_comes_from_siblings_not_from_the_gap_after_the_anchor():
    """Regression for the defect that produced the rule.

    Measuring the whitespace that *follows* the anchor is correct for a middle
    child and wrong for a last one, where the trailing gap belongs to the
    enclosing scope rather than to the sibling sequence. Here the siblings are
    separated by two blank lines while four follow the anchor; the separator
    must come from the siblings.
    """
    source = b'''def cmd_first() -> int:
    return 0


def cmd_second() -> int:
    return 0




class Unrelated:
    pass
'''
    span = locate_last_function_with_prefix(source, "cmd_")

    assert span.separator == b"\n\n\n", "separator must be the sibling gap, not the trailing one"

    result = splice_after(source, span, b"def cmd_third() -> int:\n    return 0")
    assert b"def cmd_second() -> int:\n    return 0\n\n\ndef cmd_third()" in result
    assert b"    return 0\n\n\n\n\nclass Unrelated:" in result
    ast.parse(result)


def test_a_lone_sibling_falls_back_instead_of_inventing_a_style():
    """With one child there is no rhythm to observe, and none is imposed."""
    source = b"def cmd_only() -> int:\n    return 0\n"
    span = locate_last_function_with_prefix(source, "cmd_")

    assert span.separator == b"\n"


def test_splice_before_indents_to_its_anchor_line():
    span = locate_return_in_function(MODULE, "build_parser")
    result = splice_before(MODULE, span, b"registered = True", lead=b"\n")

    assert b"    parser = object()\n\n    registered = True\n    return parser" in result
    ast.parse(result)


def test_every_pre_existing_line_survives_byte_identically():
    span = locate_last_function_with_prefix(MODULE, "cmd_")
    result = splice_after(MODULE, span, b"def cmd_third() -> int:\n    return 0")

    result_lines = result.decode().splitlines()
    for line in MODULE.decode().splitlines():
        assert line in result_lines
    assert len(result) > len(MODULE)


def test_comments_and_quote_style_survive_the_edit():
    """The reason `ast.unparse()` is banned from the mutation path."""
    source = b'''# module comment
def cmd_first() -> int:
    value = 'single quoted'  # trailing comment
    return 0
'''
    span = locate_last_function_with_prefix(source, "cmd_")
    result = splice_after(source, span, b"def cmd_second() -> int:\n    return 0")

    assert b"# module comment" in result
    assert b"'single quoted'  # trailing comment" in result


def test_missing_anchors_refuse_explicitly():
    with pytest.raises(CapabilityRefusal, match="no module-level function"):
        locate_last_function_with_prefix(b"value = 1\n", "cmd_")
    with pytest.raises(CapabilityRefusal, match="no module-level function"):
        locate_return_in_function(b"value = 1\n", "build_parser")
    with pytest.raises(CapabilityRefusal, match="has no top-level return"):
        locate_return_in_function(b"def build_parser() -> None:\n    pass\n", "build_parser")
