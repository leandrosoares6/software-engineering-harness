# Phase 0 experiment

Frozen, reproducible evidence for the Phase 0 findings. **Not part of the SEH
runtime**: nothing under `src/` imports anything here, and `pytest` with no
arguments does not collect it (`testpaths = ["tests"]`).

Conclusions live in [`../../docs/PHASE0_FINDINGS.md`](../../docs/PHASE0_FINDINGS.md);
the model they feed is [`../../docs/CAPABILITY_MODEL.md`](../../docs/CAPABILITY_MODEL.md).
This directory only makes them re-runnable.

## Running it

```bash
pytest experiments/phase0
```

## What is here

| Path | Role |
| --- | --- |
| `primitives.py` | The provisional algebra: AST locators returning byte spans, plus splice effects |
| `capabilities.py` | Three hand-authored capabilities composed from those primitives |
| `fixtures/` | Byte-exact base states, with their recorded baseline |
| `test_phase0.py` | Each finding as an executable assertion |

Capabilities are hand-written Python rather than manifests on purpose: Phase 0
asks *which primitives are needed*, and answering that must not presuppose a
schema, a CLI, or a validator.

## Fixtures are captured, not derived

`fixtures/` holds real bytes copied from the tree recorded in `fixtures/BASELINE`,
not files reconstructed from current source. That is a finding, not a
convenience — see F9. `test_fixtures_match_their_recorded_baseline` fails if a
fixture ever drifts from the hash it claims.

The fixtures deliberately do **not** track `src/`. If the product source changes,
these stay put: they record the state the evidence was produced against.

## What the tests assert

| Test group | Finding |
| --- | --- |
| insert-only, comments survive | F1 — source preservation; why `ast.unparse()` is banned from the mutation path |
| import and dispatch | F2 — generated scaffolding actually runs, and existing commands keep working |
| refusals | F3 — idempotency, missing anchor, missing scope, wrong syntactic form |
| sibling rhythm, trailing comma | F4/F5 — style derived from siblings, never imposed |
| nested collection, variable cardinality | F7 — one locator serves module-level and method-local targets |
| subtraction fixture | F9 — **asserts the failure** |

That last one is the unusual one. `test_fixture_built_by_subtraction_fails_fidelity`
passes when replay *fails* to reproduce the accepted source, because a fixture
built by deleting lines from the present describes a state that never existed. It
is written as a test so the reason Phase 0 remains open cannot quietly stop being
true.

## What this experiment does not show

- **Gate 1 (fidelity)** against a genuinely captured pre-change state.
- **Gate 2 (generalization)** against a developer-approved second event.
- Any economic result. No token, latency or payback number exists yet.

Closing conditions are listed in the checklist at the end of
[`PHASE0_FINDINGS.md`](../../docs/PHASE0_FINDINGS.md).
