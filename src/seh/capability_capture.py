from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
from typing import Callable

from .capability import SCHEMA, render_patch
from .errors import CapabilityError, CapabilityRefusal
from .git import (
    changed_files,
    file_at_commit,
    repository_root,
    resolve_commit,
    working_tree_is_clean,
)

CASE_NAMES = ("fidelity", "generalization", "refusal")

MANIFEST_SKELETON = """schema: {schema}
id: {capability_id}
version: 1

# TODO(agent): declare the typed parameters this procedure varies by.
# Only python_identifier is supported. Prose, argument lists and source code are
# not parameters — behaviour that cannot be expressed here belongs in an ordinary
# module the capability never touches.
parameters:
  name:
    type: python_identifier

# TODO(agent): a value whose presence means the procedure already ran.
preconditions:
  - uses: text.absent
    with:
      file: {first_file}
      value: "TODO"

# TODO(agent): compose the admitted primitives. Templates live under templates/.
#   splice.after   locator python.symbol    selector last_with_prefix
#   splice.before  locator python.statement statement return
steps: []

# TODO(agent): an executable check the project already trusts.
verification:
  - uses: verify.command
    with:
      executable: python
      args: ["-m", "compileall", "-q", "{first_file}"]
      timeout_seconds: 30
      expected_exit: 0
"""

SCOPE_TEMPLATE = """baseline:
  commit: {baseline}
accepted:
  commit: {accepted}
included:
{included}excluded:
{excluded}honesty_test:
  would_do_this_without_capture: "TODO(developer): yes/no, and why"
"""


def _relative(value: str) -> str:
    if not value or "\\" in value:
        raise CapabilityError(
            f"declared file must be a normalized relative path: {value!r}"
        )
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        raise CapabilityError(
            f"declared file must be a normalized relative path: {value!r}"
        )
    return path.as_posix()


def _state(root: Path, commit: str, paths: list[str]) -> dict[str, bytes]:
    state: dict[str, bytes] = {}
    for path in paths:
        content = file_at_commit(root, commit, path)
        if content is not None:
            state[path] = content
    return state


def _yaml_scalar(value: str) -> str:
    """Quote a scalar so a colon in prose cannot be read as a nested mapping."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _yaml_list(entries: list[str], reason: str) -> str:
    if not entries:
        return "[]\n"
    return "".join(
        f"- path: {_yaml_scalar(entry)}\n  reason: {_yaml_scalar(reason)}\n"
        for entry in entries
    )


def capture(
    repository_path: Path,
    output: Path,
    *,
    capability_id: str,
    baseline: str,
    declared: list[str],
) -> tuple[Path, list[str], list[str]]:
    """Materialize a candidate skeleton from an accepted change.

    Reads the true `before` bytes from the recorded baseline commit. It never
    reconstructs them by subtracting from the current tree, because ordering and
    surrounding bytes are historical facts.

    Templates, parameters and steps are deliberately left as TODO: separating
    structure from domain is the agent's judgement, and SEH must not infer it.
    """
    root = repository_root(repository_path)
    if not working_tree_is_clean(root):
        raise CapabilityRefusal(
            "working tree is not clean; commit or stash the accepted change before capture"
        )

    base = resolve_commit(root, baseline)
    accepted = resolve_commit(root, "HEAD")
    if base == accepted:
        raise CapabilityRefusal(
            "baseline and HEAD are the same commit; nothing was accepted"
        )

    declared_paths = [_relative(item) for item in declared]
    if not declared_paths:
        raise CapabilityError("at least one --file must be declared")

    changed = changed_files(root, base, accepted)
    if not changed:
        raise CapabilityRefusal("no files changed between the baseline and HEAD")

    unknown = [path for path in declared_paths if path not in changed]
    if unknown:
        raise CapabilityRefusal(
            "declared files did not change between baseline and HEAD: "
            + ", ".join(unknown)
        )

    if output.exists():
        raise CapabilityError(f"output directory already exists: {output}")

    # Both patches come from the same renderer, so the structural subset is
    # contained in the accepted change by construction rather than by assertion.
    all_before = _state(root, base, changed)
    all_after = _state(root, accepted, changed)
    declared_before = {
        path: all_before[path] for path in declared_paths if path in all_before
    }
    declared_after = {
        path: all_after[path] for path in declared_paths if path in all_after
    }

    accepted_patch = render_patch(all_before, all_after)
    expected_patch = render_patch(declared_before, declared_after)
    excluded = [path for path in changed if path not in declared_paths]

    scope = SCOPE_TEMPLATE.format(
        baseline=base,
        accepted=accepted,
        included=_yaml_list(
            declared_paths, "TODO(agent): why this is recurring structure"
        ),
        excluded=_yaml_list(
            excluded, "TODO(developer): why this is behavioural work"
        ),
    )

    output.mkdir(parents=True)
    (output / "templates").mkdir()
    (output / "capability.yaml").write_text(
        MANIFEST_SKELETON.format(
            schema=SCHEMA, capability_id=capability_id, first_file=declared_paths[0]
        ),
        encoding="utf-8",
    )

    for case in CASE_NAMES:
        case_root = output / "examples" / case
        (case_root / "before").mkdir(parents=True)
        for path, content in declared_before.items():
            target = case_root / "before" / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        approved = "\napproved: true\n" if case == "generalization" else "\n"
        (case_root / "case.yaml").write_text(
            f"parameters:\n  name: TODO{approved}", encoding="utf-8"
        )
        if case == "refusal":
            continue
        (case_root / "accepted.patch").write_text(accepted_patch, encoding="utf-8")
        (case_root / "expected.patch").write_text(expected_patch, encoding="utf-8")
        (case_root / "scope.yaml").write_text(scope, encoding="utf-8")

    return output, declared_paths, excluded


def execute(args: argparse.Namespace) -> int:
    output, declared, excluded = capture(
        Path(args.repo or "."),
        Path(args.output),
        capability_id=args.id,
        baseline=args.baseline,
        declared=args.file,
    )
    print(f"Captured candidate at {output}")
    print(f"  declared structural surface: {len(declared)} file(s)")
    for path in declared:
        print(f"    {path}")
    print(f"  excluded as behavioural work: {len(excluded)} file(s)")
    print()
    print("Fixtures and patches are final. Still to author, by the agent:")
    print("  - templates/ for each step")
    print("  - parameters, preconditions and steps in capability.yaml")
    print("  - the second case in examples/generalization/, for the developer to approve")
    print("  - an incompatible tree in examples/refusal/before/")
    return 0


def configure_parser(
    subcommands: argparse._SubParsersAction,
    handler: Callable[[argparse.Namespace], int],
) -> None:
    command = subcommands.add_parser(
        "capture", help="materialize a candidate skeleton from an accepted change"
    )
    command.add_argument(
        "--id", required=True, help="capability id, e.g. app.add-registry-handler"
    )
    command.add_argument(
        "--baseline", required=True, help="commit the accepted change started from"
    )
    command.add_argument(
        "--file",
        action="append",
        default=[],
        required=True,
        metavar="PATH",
        help="a file forming the recurring structural surface; repeat per file",
    )
    command.add_argument(
        "--output", required=True, help="directory to create for the candidate"
    )
    command.add_argument("--repo")
    command.set_defaults(handler=handler)
