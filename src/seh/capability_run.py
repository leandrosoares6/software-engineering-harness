from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from .capability_operation import run_capability
from .errors import CapabilityError


def _parameters(pairs: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for pair in pairs:
        name, separator, value = pair.partition("=")
        if not separator or not name:
            raise CapabilityError(f"parameter must be given as name=value: {pair!r}")
        if name in values:
            raise CapabilityError(f"parameter given twice: {name}")
        values[name] = value
    return values


def execute(args: argparse.Namespace) -> int:
    operation = run_capability(
        args.capability_id,
        _parameters(args.param),
        Path(args.repo or "."),
        apply=args.apply,
        allow_verification=args.allow_verification,
    )
    if not operation.applied:
        print(
            f"Planned {operation.capability_id} v{operation.version} "
            f"({len(operation.files)} file(s), nothing written)"
        )
        print(f"Operation {operation.operation_id}")
        print(operation.patch, end="")
        print("Rerun with --apply --allow-verification to write and verify this patch.")
        return 0
    verified = "verified" if operation.verified else "not verified"
    print(
        f"Applied {operation.capability_id} v{operation.version} "
        f"to {len(operation.files)} file(s), {verified}, "
        f"in {operation.duration_ms}ms"
    )
    print(f"Operation {operation.operation_id}")
    for path in operation.files:
        print(f"  {path}")
    return 0


def configure_parser(
    subcommands: argparse._SubParsersAction,
    handler: Callable[[argparse.Namespace], int],
) -> None:
    command = subcommands.add_parser(
        "run", help="instantiate an installed capability against the repository"
    )
    command.add_argument("capability_id", help="identifier of an installed capability")
    command.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="capability parameter; repeat for each declared parameter",
    )
    command.add_argument("--repo")
    command.add_argument(
        "--apply",
        action="store_true",
        help="write the patch; without it the operation only plans",
    )
    command.add_argument(
        "--allow-verification",
        action="store_true",
        help="execute reviewed verify.command entries (not sandboxed)",
    )
    command.set_defaults(handler=handler)
