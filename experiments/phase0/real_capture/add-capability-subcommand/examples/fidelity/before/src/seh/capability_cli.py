from __future__ import annotations

import argparse
from pathlib import Path

from .capability import validate_candidate
from .errors import CapabilityValidationError


def cmd_validate(args: argparse.Namespace) -> int:
    report = validate_candidate(
        Path(args.candidate), allow_verification=args.allow_verification
    )
    print(f"Capability {report.capability_id}")
    for gate in report.gates:
        status = "PASS" if gate.passed else "FAIL"
        print(f"  {status:4} {gate.name}: {gate.detail}")
    if not report.passed:
        failed = ", ".join(gate.name for gate in report.gates if not gate.passed)
        raise CapabilityValidationError(f"capability validation failed: {failed}")
    return 0


def configure_capability_parser(subcommands: argparse._SubParsersAction) -> None:
    capability_command = subcommands.add_parser(
        "capability", help="validate and manage deterministic project capabilities"
    )
    capability_subcommands = capability_command.add_subparsers(
        dest="capability_command", required=True
    )

    validate_command = capability_subcommands.add_parser(
        "validate", help="run the four gates against a reviewed candidate"
    )
    validate_command.add_argument(
        "candidate", help="path to the capability candidate directory"
    )
    validate_command.add_argument(
        "--allow-verification",
        action="store_true",
        help="execute reviewed verify.command entries (not sandboxed)",
    )
    validate_command.set_defaults(handler=cmd_validate)
    return None
