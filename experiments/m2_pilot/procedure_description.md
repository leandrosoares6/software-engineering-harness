# How this project adds a `seh capability` subcommand

This is the **Arm A′ treatment** for the M2 pilot: the prose a project would write in its own contributor
documentation to describe a recurring procedure. It is derived from the accepted `install` change that
`seh.add-capability-subcommand` was captured from.

It is deliberately calibrated to describe the *same surface the capability encodes* — no more, no less.
Making it vaguer would inflate the measured SEH effect; enriching it beyond the capability would deflate it.
Its wording is part of the benchmark manifest, and changing it invalidates a run in progress.

---

Every subcommand under `seh capability` follows the same shape. Command behaviour lives in its own module;
`capability_cli.py` holds only the wiring that connects it.

## The module

A subcommand named `X` lives in `src/seh/capability_X.py` and exposes exactly two things:

- `execute(args: argparse.Namespace) -> int` — the behaviour;
- `configure_parser(subcommands, handler) -> None` — which calls `subcommands.add_parser("X", help=...)`,
  declares that command's own arguments, and ends with `command.set_defaults(handler=handler)`.

`configure_parser` receives the handler as a parameter rather than importing it, because
`capability_cli.py` already imports this module and the reverse import would be circular.

Help text, arguments, presentation and behaviour all belong here. None of them belong in the wiring.

## The wiring

`src/seh/capability_cli.py` gains exactly two fragments, and nothing else in that file changes.

**A handler**, placed after the last existing `cmd_*` function at module level. It is a thin adapter with no
logic of its own:

```python
def cmd_X(args: argparse.Namespace) -> int:
    from .capability_X import execute

    return execute(args)
```

**A registration**, placed inside `configure_capability_parser`, immediately before its `return None`, and
separated from the preceding block by a blank line:

```python
    from .capability_X import configure_parser as configure_X_parser

    configure_X_parser(capability_subcommands, cmd_X)
```

Both imports are local to their function. That keeps the module-level import block untouched, so adding a
subcommand never edits an import list.

## Conventions that apply

- Two blank lines between module-level functions, matching the rest of the file.
- The subcommand name, the module name, the handler name and the alias all derive from the same identifier.
- Existing subcommands keep working unchanged; this file is only ever appended to.
