# Correctness probe: A′ vs B

**Status: probe, not the pilot.** It answers one question the pilot would also answer, and says nothing about
economics. Run 2026-08-12 against base commit `84b521a`.

## Why a probe instead of the pilot

The M2 pilot needs the measurement harness (protocol increments 1–3), fresh sessions, and provider-native
token accounting. None of that exists yet. But the single scenario that most threatens the product thesis
needs none of it:

> Does a cold agent, given only a prose description of the procedure, produce the same wiring the capability
> produces?

That is answerable by comparing bytes.

## Method

Task `t1-uninstall` from the pilot manifest: add an `uninstall` subcommand to the `seh capability` group.
Two cold subagents, each in an isolated copy of the repository at `84b521a`, with `.seh-capabilities/` and
`experiments/m2_pilot/` removed.

| Arm | Treatment |
| --- | --- |
| A | task prompt only |
| A′ | task prompt plus `procedure_description.md`, inline |
| B | not run as an agent — the capability's output is deterministic and was computed directly |

Comparison is scoped to `src/seh/capability_cli.py`, the structural surface the capability claims. The
command module and its tests are behavioural work the capability never produces.

## Result

**Both arms produced wiring byte-identical to the capability's output, and to each other.**

```text
arm_a        byte-identical to capability: True
arm_a_prime  byte-identical to capability: True
```

Observed cost, for the whole task rather than the wiring alone:

| | tokens | tool uses | wall clock |
| --- | --- | --- | --- |
| A | 123,658 | 54 | 972 s |
| A′ | 96,656 | 27 | 296 s |
| A → A′ | −21.8% | −50% | −69.6% |

## What this establishes

**Correctness parity, for this task shape.** The capability's value here is not that it produces correct
wiring where an agent would not. A competent cold agent produced exactly the same bytes. Whatever the
capability is worth on this task is confined to the tokens and latency of the wiring portion — 10 lines of
the ~350–490 each arm wrote.

This substantially confirms the scenario that most threatened the thesis: for a well-documented two-fragment
procedure, the prose is enough.

## What this does not establish

- **Nothing about A′ → B.** Arm B was never run as an agent, so the economic claim remains unmeasured.
- **Nothing about drift.** An agent correct today may be wrong after the convention changes; a capability
  refuses instead of guessing. This probe is a single point in time.
- **Nothing about scale.** One capability, no selection cost. With thirty, retrieval becomes the problem.
- **Nothing about harder shapes.** Two fragments in one file is the easiest possible case.

## Confounds, including one that invalidates an arm

**Arm A is not a clean baseline and must not be read as one.** Its agent reported finding and using
`experiments/phase0/real_capture/add-capability-subcommand/` — the capability package itself — as the source
of the convention. It effectively received the A′ treatment and more. `docs/CAPABILITY_MODEL.md` also
describes the procedure. This repository documents its own conventions thoroughly, so a genuine
no-documentation arm is not constructible here without making the subject unrealistic.

**Scope differed between arms.** Arm A additionally refactored `capability_catalog.py`, adding 97 lines and
extracting shared helpers; Arm A′ did not. The token and time deltas therefore mix a documentation effect
with a scope choice, and cannot be attributed to the treatment.

**n = 1 per arm.** No repetition, so model nondeterminism is uncontrolled. These are observations, not
estimates.

## An unexpected finding

The Arm A agent used the **installed capability package as documentation**, reading its templates and
manifest to infer the convention without executing anything. A capability therefore has value as a
machine-readable statement of a project's convention, separate from its value as an executable operation.
Nobody had recorded that hypothesis, and it is far cheaper to obtain than the execution path.

## Cost to the pilot

`t1-uninstall` is now burned as a pilot task: two agents have solved it and the solution is recorded here.
When the harness exists, the manifest must either replace it or declare the contamination. A substitute must
pass the same test as the originals — something the project would build regardless of the benchmark.
