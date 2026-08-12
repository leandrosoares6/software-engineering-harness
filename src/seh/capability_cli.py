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


def cmd_install(args: argparse.Namespace) -> int:
    from .capability_install import execute

    return execute(args)


def cmd_run(args: argparse.Namespace) -> int:
    from .capability_run import execute

    return execute(args)


def cmd_capture(args: argparse.Namespace) -> int:
    from .capability_capture import execute

    return execute(args)


def cmd_list(args: argparse.Namespace) -> int:
    from .capability_list import execute

    return execute(args)


def cmd_show(args: argparse.Namespace) -> int:
    from .capability_show import execute

    return execute(args)


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

    from .capability_install import configure_parser as configure_install_parser

    configure_install_parser(capability_subcommands, cmd_install)

    from .capability_run import configure_parser as configure_run_parser

    configure_run_parser(capability_subcommands, cmd_run)

    from .capability_capture import configure_parser as configure_capture_parser

    configure_capture_parser(capability_subcommands, cmd_capture)

    from .capability_list import configure_parser as configure_list_parser

    configure_list_parser(capability_subcommands, cmd_list)

    from .capability_show import configure_parser as configure_show_parser

    configure_show_parser(capability_subcommands, cmd_show)
    return None
