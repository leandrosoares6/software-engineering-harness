from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from .capability import Candidate, Invocation, load_candidate
from .capability_catalog import CATALOG_DIRECTORY
from .errors import CapabilityError
from .git import repository_root

MAX_TEMPLATE_PREVIEW_BYTES = 4096


def resolve(
    repository_path: Path, *, path: str | None, capability_id: str | None
) -> Candidate:
    if (path is None) == (capability_id is None):
        raise CapabilityError("provide either a candidate path or --id, not both")
    if path is not None:
        return load_candidate(Path(path))
    root = repository_root(repository_path)
    destination = root / CATALOG_DIRECTORY / capability_id
    if destination.is_symlink():
        raise CapabilityError(
            f"installed capability must not be a symlink: {destination}"
        )
    if not destination.is_dir():
        raise CapabilityError(f"capability is not installed: {capability_id}")
    return load_candidate(destination)


def _describe(invocation: Invocation, index: int) -> str:
    config = invocation.config
    if invocation.uses == "splice.after":
        target = f"after last `{config['prefix']}*` in {config['file']}"
    elif invocation.uses == "splice.before":
        target = f"before `return` in {config['function']}() of {config['file']}"
    else:
        target = str(config.get("file", ""))
    return f"  {index + 1}. {invocation.uses:14} {target}"


def render(candidate: Candidate) -> list[str]:
    """Everything a reviewer must see before granting --allow-verification."""
    lines = [
        f"Capability {candidate.capability_id} v{candidate.version}",
        f"  package: {candidate.root}",
        "",
        "Parameters",
    ]
    for name, kind in sorted(candidate.parameters.items()):
        lines.append(f"  {name}: {kind}")

    lines += ["", "Preconditions"]
    for invocation in candidate.preconditions:
        config = invocation.config
        lines.append(
            f"  {invocation.uses}: {config.get('value')!r} "
            f"must be absent from {config.get('file')}"
        )

    lines += ["", "Steps"]
    for index, invocation in enumerate(candidate.steps):
        lines.append(_describe(invocation, index))
        lines.append(f"       template: {invocation.config['template']}")

    # The reason this command exists. A reviewer granting --allow-verification is
    # trusting these processes with their own privileges, so they are printed in
    # full: never summarized, never truncated.
    lines += ["", "Verification commands — these WILL execute with your privileges"]
    for invocation in candidate.verification:
        config = invocation.config
        argv = " ".join([config["executable"], *config["args"]])
        lines.append(f"  $ {argv}")
        lines.append(
            f"    timeout {config['timeout_seconds']}s, "
            f"expects exit {config['expected_exit']}"
        )
    lines.append("  (no shell, argument vector only — this is not an OS sandbox)")

    lines += ["", "Templates"]
    for invocation in candidate.steps:
        relative = invocation.config["template"]
        lines.append(f"  {relative}")
        try:
            content = (candidate.root / relative).read_bytes()
        except OSError as exc:
            lines.append(f"    <unreadable: {exc}>")
            continue
        preview = content[:MAX_TEMPLATE_PREVIEW_BYTES]
        text = preview.decode("utf-8", errors="replace")
        lines.extend(f"    | {line}" for line in text.splitlines())
        if len(content) > MAX_TEMPLATE_PREVIEW_BYTES:
            lines.append(f"    | ... truncated at {MAX_TEMPLATE_PREVIEW_BYTES} bytes")

    return lines


def execute(args: argparse.Namespace) -> int:
    candidate = resolve(
        Path(args.repo or "."), path=args.candidate, capability_id=args.capability_id
    )
    for line in render(candidate):
        print(line)
    return 0


def configure_parser(
    subcommands: argparse._SubParsersAction,
    handler: Callable[[argparse.Namespace], int],
) -> None:
    command = subcommands.add_parser(
        "show",
        help="print a capability's manifest, templates and declared commands "
        "without running them",
    )
    selection = command.add_mutually_exclusive_group(required=True)
    selection.add_argument("candidate", nargs="?", help="path to a candidate package")
    selection.add_argument(
        "--id", dest="capability_id", help="an installed capability id"
    )
    command.add_argument("--repo")
    command.set_defaults(handler=handler)
