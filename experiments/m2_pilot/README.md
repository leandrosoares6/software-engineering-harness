# M2 instrumentation pilot

Pre-registration for the first economic measurement. The contract it instantiates is
[`../../docs/M2_MEASUREMENT_PROTOCOL.md`](../../docs/M2_MEASUREMENT_PROTOCOL.md).

`manifest.yaml` is written **before** the runner that reads it and before any data is collected. That order
is the point: a manifest produced alongside its results can be tuned to them.

## What this pilot can and cannot conclude

It is an **instrumentation pilot**. Its job is to expose missing token fields, order effects, unstable
acceptance checks and obviously weak economics — not to produce a defensible economic claim.

| | |
| --- | --- |
| Can conclude | whether the harness records complete, comparable traces; the direction and rough size of `A′ → B` |
| Cannot conclude | payback, significance, generalization to other capabilities, projects, agents or models |

`payback.claimed` is `false`, and that is not a formality. The retained capability was authored before M2
instrumentation existed, so its authoring cost is historical. The protocol forbids reconstructing it, so this
pilot measures marginal execution only. Payback needs a capability captured prospectively — the natural
content of a second pilot.

## Decisions taken, and why

**The POC is SEH itself.** Building a repository to host the tasks would manufacture the recurrence this
project has twice learned not to manufacture. The cost is task leakage: the five tasks are siblings of the
`install` event the capability was captured from, which makes them maximally favourable to it. That is
declared in the manifest rather than mitigated.

**Five tasks, all wanted anyway.** `show`, `list`, `uninstall`, `verify`, `export`. Each closes a real gap —
`show` in particular addresses the review affordance that `--allow-verification` currently demands without
supporting. If any of them stops being something the project would build regardless, it must leave the task
set rather than be justified after the fact.

**Three arms, `R = 3`.** Arm A′ exists so the verdict measures determinism rather than the mere knowledge
that a procedure exists — that knowledge is reproducible with a paragraph and no product. Three repetitions
per cell are the minimum that makes within-cell dispersion observable at all, and that is the variance
component a confirmatory sample size must be derived from.

**Single-capability catalogue, declared.** Selection is pre-resolved, so Arm B is an upper bound rather than
an estimate. A decoy would have to be structurally applicable to the same base tree while being semantically
wrong for the prompt: a non-applicable decoy is removed by the deterministic filter before the agent sees it
and would measure nothing. None is authored yet, so the manifest sets `selection_cost_measured: false`.

## What blocks collection

Every `REQUIRED-BEFORE-COLLECTION` field. They fall into three groups.

**Only you can decide**
- `environment.agent`, `agent_version`, `model`, `provider` — which of the three agents supplies the first
  complete usage trace, pinned to a version;
- `retention.retention_days`, `redaction_patterns` — what is safe to keep locally;
- `arm_a_prime.author` and `reviewer`.

**Mechanical, once the agent is chosen**
- `adapter` — depends on which provider-native usage fields are exposed;
- `application_file_fingerprint`, `dependency_lock`, `package_sha256`, `procedure_description_sha256`;
- `order_seed`.

**A judgement call before the first run**
- `task_timeout_seconds` — long enough that a slow arm is not truncated, short enough that a stuck agent does
  not dominate wall time. A timeout is a task failure, never an infrastructure exclusion, so this value
  shapes the result directly;
- `confirmatory_sample_size_trigger` — the dispersion that would justify a larger confirmatory run.

`procedure_description.md` does not exist yet. It is the Arm A′ treatment and must be written and reviewed
before the pilot, from the same accepted `install` change the capability came from.

## Sequence

1. resolve the blocking fields and write `procedure_description.md`;
2. implement increment 1 of the protocol handoff — evidence schemas and local storage, test-driven;
3. implement the adapter and recorder, then the runner;
4. run 45 attempts and inspect within-cell and between-task dispersion separately;
5. publish a sanitized report whose headline verdict is `A′ → B` and whose catalogue size is stated.

Nothing before step 1 should touch an agent or collect an ad hoc trace.
