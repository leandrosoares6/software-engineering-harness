from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from .capability_catalog import install_candidate
from .errors import CapabilityValidationError


def execute(args: argparse.Namespace) -> int:
    try:
        installation = install_candidate(
            Path(args.candidate),
            Path(args.repo or "."),
            allow_verification=args.allow_verification,
        )
    except CapabilityValidationError as exc:
        if exc.report is not None:
            for gate in exc.report.gates:
                status = "PASS" if gate.passed else "FAIL"
                print(f"  {status:4} {gate.name}: {gate.detail}")
        raise
    print(
        f"Installed {installation.report.capability_id} "
        f"v{installation.version} "
        f"at {installation.destination}"
    )
    if installation.report.provenance is not None:
        # What enters the catalogue is versioned procedural memory, so how
        # strongly it is anchored to history belongs in the install record, not
        # only in a validate run the reviewer may never have seen.
        provenance = installation.report.provenance
        print(f"  {provenance.status}: {provenance.detail}")
    return 0


def configure_parser(
    subcommands: argparse._SubParsersAction,
    handler: Callable[[argparse.Namespace], int],
) -> None:
    command = subcommands.add_parser(
        "install", help="validate and atomically promote a reviewed candidate"
    )
    command.add_argument("candidate", help="path to the capability candidate directory")
    command.add_argument("--repo")
    command.add_argument(
        "--allow-verification",
        action="store_true",
        help="execute reviewed verify.command entries (not sandboxed)",
    )
    command.set_defaults(handler=handler)
