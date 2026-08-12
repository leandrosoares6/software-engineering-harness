# M2 Measurement Protocol

Status: **implementation contract for the first economic experiment**.

Phase 0 established technical feasibility: a capability derived from an accepted event reproduced its
structural patch, generalized to a developer-approved second event, remained idempotent, and refused an
incompatible repository. M2 tests the independent economic hypothesis. It must produce a number even when
that number is unfavorable.

## Capability

M2 gives a developer and product reviewer a reproducible way to compare ordinary agentic implementation
with SEH-assisted execution of an already learned procedure. For each task, the harness records provenance,
quality, token usage, wall-clock latency, tool activity, and deterministic operation evidence. It then
reports marginal savings and how many successful reuses are required to repay capability authoring.

The experiment answers:

> After paying once to create and validate a capability, how many compatible repetitions are required to
> recover its authoring cost in tokens and elapsed time without reducing completion quality?

The first experiment measures the real benefit demonstrated by `add-capability-subcommand`: avoiding
rediscovery of placement and structural shape. It does **not** use generated-line count as a value proxy. The
captured structural subset was 1.2% of its accepted change; the expected benefit is fewer repository reads,
tool calls, retries, and inference round-trips.

## Hypotheses and decision rule

Hypothesis B retains the provisional thresholds already defined by the product PRD:

- at least **30% fewer measured tokens** in the SEH arm, against the documented arm (`A′ → B`);
- at least **50% less task wall-clock time** in the SEH arm, against the documented arm (`A′ → B`);
- completion quality equal to or better than both the baseline and documented arms;
- capability payback in at most **five successful marginal invocations** as the initial product target.

These thresholds are bets, not facts. The report always includes raw results and dispersion, including when
the thresholds fail.

The outcome has three branches:

1. **Quality regresses:** the economic comparison is invalid. A faster incorrect change is not a saving.
2. **Quality holds, thresholds fail:** procedural memory works but has not justified the original individual
   developer/token-cost promise. Consider a governance or onboarding use case, or revise the product thesis.
3. **Quality holds and thresholds pass:** the economic hypothesis passes for the measured agent, project,
   capability, and task population only. Generalization requires more capabilities and projects.

Passing the pilot is not a universal performance claim.

## Fixed constraints

The following rules are policy for the first benchmark:

1. **SEH never calls a model.** Agent inference remains outside the product and is observed through an
   adapter.
2. **One agent integration first.** Cross-agent normalization is deferred until one adapter produces complete
   traces reliably.
3. **Same task, same application base state.** Every attempt in a block starts from the same committed
   application tree and dependency lock state. The procedure description is an Arm A′ treatment and the
   installed capability an Arm B treatment; both are hashed and prepared before timing, neither belongs to
   Arm A, and neither alters application files.
4. **Fresh session for every trial.** No conversation, tool cache, or result from one arm may leak into the
   other.
5. **Quality is executable.** A task is complete only when its predefined acceptance command succeeds and
   its repository assertions hold. An LLM or human does not grade correctness.
6. **Planning and application are distinct.** SEH operation planning, application, and verification durations
   are recorded separately even when the user observes only total wall time.
7. **Missing measurement is not zero.** An unavailable token field is `null`; a trial without required token
   accounting is excluded from the token comparison and retained for other metrics.
8. **Raw and normalized data coexist.** Provider-native usage fields are preserved alongside a small common
   projection so later normalization changes do not rewrite history.
9. **Setup, authoring, and marginal execution are separate costs.** Combining them would hide the payback
   curve.
10. **Runtime evidence is local derived state.** Raw prompts, tool logs, and benchmark records live under
    ignored `.seh/`; only sanitized aggregate reports or deliberately synthetic fixtures may be committed.
11. **No silent staleness.** Every record binds to schema version, repository root, base commit/tree,
    capability version, operation ID where applicable, agent identity, and benchmark configuration.
12. **No model-filled code slots.** A measured SEH operation is deterministic. Any subsequent novel edit by
    the agent is a separate phase and a separate cost.

## Experimental design

### Unit of observation

The unit is one **task attempt**:

```text
fixed developer prompt
  + fresh agent session
  + canonical repository base tree
  + assigned arm
  → accepted result or explicit failure
```

A **block** contains one attempt in each arm — A, A′ and B — for the same task instance and base tree. A
**pair** is any two arms within a block compared against each other; `A′ → B` is the pair that carries the
economic verdict. Task instances vary the capability parameter and expected artifact while preserving
equivalent difficulty.

Because a single attempt cannot separate task difficulty from model nondeterminism, every arm of a block is
run **`R` times** (see *Pilot size*). A cell is one `(task, arm)` combination and holds `R` attempts.

### Arms

#### Arm A — baseline agent

The agent receives the developer prompt and normal repository tools. It may inspect, search, edit, and run
the declared acceptance command. Its workspace contains no capability treatment overlay, generated patch,
captured examples, procedure description, or result from any other arm.

This arm represents repeatedly rediscovering how the project performs the procedure.

#### Arm A′ — documented agent

The agent receives the developer prompt, normal repository tools, and a prose description of the recurring
procedure: which files participate, in what order, and what the result must look like. It has no installed
capability, no deterministic operation, and no generated patch.

This arm exists because Arm B receives **two** things Arm A does not: the knowledge that the procedure exists
and what it is, and the deterministic execution of it. Only the second is SEH. The first is reproducible with
a paragraph in a project instruction file, at no cost and with no product.

Comparing only A against B attributes the whole difference to determinism and would overstate it. Three arms
separate the two effects:

```text
A  → A′    value of knowing the procedure          (documentation)
A′ → B     value of executing it deterministically (SEH)
```

The prose description is derived from the same accepted change the capability was captured from, and reviewed
so that it is neither deliberately vague nor enriched beyond what the capability encodes. Its exact text
belongs to the benchmark manifest and is published with the report.

The headline economic verdict for Hypothesis B is the **A′ → B** comparison. The A → B figure is reported
alongside it as the total effect a project sees when it adopts SEH with no prior documentation.

#### Arm B — SEH-assisted agent

The agent receives the same developer prompt plus the compact capability projection needed to select the
applicable capability. It supplies parameters, reviews the operation plan, applies it with explicit
verification consent, and reports the resulting evidence. It may use ordinary tools when the capability
refuses or when the task contains explicitly separated novel work; those actions remain in the measured
trace and are not hidden from the comparison.

The arm records both total task cost and the inner deterministic operation cost.

##### Selection is measured at its best case

With a single installed capability, selection is trivial: retrieval cost is near zero and choosing wrongly is
impossible. That is not noise. It is a bias with a known direction, and it inflates Arm B in exactly the
dimension a real catalogue makes harder.

The pilot therefore reports its Arm B result as an **upper bound on the SEH effect, not an estimate**, and
states the catalogue size next to every headline figure. Two mitigations are available and the manifest must
record which was used:

1. **Decoy catalogue** — install additional capabilities that the agent must actually choose between.
   Preferred, because it makes selection cost and selection error observable at low expense.

   A decoy only works if it **survives the deterministic applicability filter**. SEH removes non-applicable
   capabilities before the agent ever sees them, so a decoy that fails preconditions is filtered out and
   measures nothing. A valid decoy is *structurally applicable* — its preconditions hold against the same
   base tree — and *semantically wrong* for this prompt: it targets the same anchors but expresses a
   different engineering intent, and choosing it would produce a real but incorrect change.

   The manifest records each decoy, the evidence that it passed the applicability filter for the task, and
   how many capabilities the agent's projection actually contained.

2. **Declared single-capability catalogue** — keep one capability and label the result
   `selection cost not measured`.

Catalogue retrieval is an unsolved problem recorded in the roadmap (M5). The pilot does not solve it; it must
not accidentally claim to have avoided it either.

### Authoring observation

Both treatments are authored, and both are measured. Arm A′ has a setup cost as real as Arm B's; treating the
procedure description as free would inflate the capability's apparent payback.

**Procedure description authoring** is measured once. Its interval begins when the accepted change is
selected as the source of the description and ends when the text is reviewed and accepted into the manifest.
It records agent tokens where a model helped draft it, automated wall time, and developer authoring and
review time, each separately.

**Capability creation** is measured once, separately from task blocks. Its interval begins when an eligible
accepted change is selected for capture and ends when the capability is validated, developer-approved, and
installed. It records:

- agent input, output, cache, and reasoning tokens where exposed;
- agent and tool wall-clock duration;
- SEH validation and installation duration;
- number and duration of failed candidate revisions;
- developer review duration, reported separately from automated duration;
- changed files and final capability package bytes.

The existing historical Phase 0 chain proves provenance but predates M2 instrumentation. It cannot be used
as a fabricated numeric authoring baseline. The first economic POC must capture authoring prospectively or
mark authoring cost unavailable and refrain from claiming payback.

### Pairing, order, and isolation

For every task instance:

1. create one disposable worktree, or equivalent isolated copy, per attempt at the declared application base
   commit;
2. install identical locked dependencies before the timed task interval, recording setup separately;
3. supply the procedure description only to Arm A′ attempts, and install the declared capability package only
   as the Arm B treatment overlay, verifying its package hash;
4. confirm that the application-file fingerprint remains identical across all arms;
5. assign the execution order of every attempt in the block using a recorded seed, so that no arm is
   systematically first or last;
6. launch a fresh agent session with fixed model, agent version, settings, tool permissions, and system
   instructions;
7. start the task timer immediately before dispatching the developer prompt;
8. stop it when deterministic acceptance succeeds, the agent declares failure, or the timeout expires;
9. preserve every result tree and its evidence until assertions and trace ingestion finish;
10. discard the worktrees after the benchmark record is durably written.

Warm model-provider caches may exist outside local control. Record cache tokens and execution order so their
effect is visible. Do not intentionally warm one arm with another arm's prompt or output.

### Pilot size

The first implementation uses **at least five task instances**, each run **three times per arm** — five
blocks, three arms, `R = 3`, so at least 45 attempts. This is enough to expose missing fields, order effects,
unstable acceptance checks, and obviously weak economics; it is not enough for a broad statistical claim.

Repetition is not padding. Two different sources of variation drive the result and only one of them is
interesting:

- **between tasks** — some instances are genuinely harder than others;
- **within a cell** — the same prompt, same arm and same base tree still cost differently because the model
  is nondeterministic.

With one attempt per cell the two are indistinguishable, so a confirmatory sample size derived from that
pilot would be based on the wrong variance component. `R = 3` is the minimum that makes within-cell
dispersion observable at all; report it per cell rather than collapsing it early.

#### Aggregating quality and cost across repetitions

Cost and quality aggregate differently, and conflating them would let a partly failing cell contribute a
flattering median.

**Quality is counted per attempt.** Completion rate is attempts accepted over attempts run, per arm. An
attempt that fails is never absorbed into a cell median.

**A cell is accepted only when all `R` of its attempts are accepted.** Anything less makes the cell's cost
unrepresentative: the median would describe only the runs that happened to work.

**A block enters the economic comparison only when all three of its cells are accepted** — that is, all `3R`
attempts succeeded. Blocks that do not qualify stay in full in the quality report, with their per-attempt
outcomes and failure reasons, and are excluded only from cost aggregation. The report states how many blocks
were economically eligible out of how many were scheduled; a low ratio is itself a finding.

This rule protects cost comparability, but it is **not** a conservative safeguard and its bias has no known
direction. Excluding a block whenever any arm failed cuts both ways:

- Arm A′ fails, Arm B succeeds → a real B advantage disappears, hiding an effect;
- Arm B fails, Arm A′ succeeds → a real B disadvantage disappears, flattering B.

Which dominates depends on which arm fails more often, which is exactly what the experiment is trying to
find out. The honest statement is that complete-case aggregation **changes the estimand**: the reported
economics describe blocks *in which every arm completed*, not the task population as a whole.

The report must therefore state the estimand explicitly, publish the per-arm failure counts that produced the
exclusions, and never present the cost result as if it applied to all scheduled tasks.

Within an eligible cell, aggregate to a single value with the **median of its `R` attempts** before computing
block deltas, and publish the within-cell range alongside it.

After the pilot, choose the confirmatory sample size from the observed within-cell and between-task
dispersion separately, and record that decision before collecting confirmatory results. Until that decision
exists, reports must label results `pilot` and avoid significance language.

## POC project and task eligibility

The POC must be a Python repository with locked dependencies, deterministic local acceptance commands, and a
procedure that genuinely recurs across independent task instances. It may be a dedicated fixture project,
but it must contain enough surrounding structure for repository exploration to be real rather than a
single-file toy.

Each task instance must declare:

- stable task ID and developer prompt;
- canonical base commit and tree;
- capability ID/version and parameters for Arm B;
- files the task is allowed to change;
- deterministic repository assertions;
- focused acceptance command and timeout;
- whether any domain-specific edit is excluded from the deterministic operation;
- a difficulty/block label used for pairing or stratification.

An instance is ineligible when its expected result or capability patch is already visible to Arm A, when its
base tree differs between arms, when acceptance depends on a network service, or when the capability's local
preconditions do not match the declared base state.

The initial `add-capability-subcommand` POC tests the mechanism's measured value, not primitive-vocabulary
coverage. Before making a product-wide claim, repeat the protocol with a capability of a genuinely different
shape.

## Metric contract

### Primary metrics

#### Task wall-clock latency

Measured with a monotonic clock from prompt dispatch to deterministic acceptance, explicit failure, or
timeout:

```text
task_wall_ms = accepted_at_monotonic - prompt_dispatched_at_monotonic
```

Also record agent-visible inference time, tool time, SEH plan/apply/verify time, and acceptance time when the
adapter can separate them. Provider queue time remains part of the user-observed total.

#### Token consumption

Preserve provider-native fields and normalize, when available:

```text
input_tokens
output_tokens
cache_read_tokens
cache_write_tokens
reasoning_tokens
```

The default comparison is `input_tokens + output_tokens + reasoning_tokens` plus any provider-specific billed
input category. Cache reads/writes are reported separately and included in a second "provider total" only
when the provider documents their billing semantics. The report must print its exact formula.

Never estimate agent tokens from bytes in the primary result. Byte-based estimates may appear only as a
diagnostic and must identify their algorithm.

#### Completion quality

Quality is a guard, not a weighted score. A successful task requires all of:

- agent/session exits without infrastructure failure;
- acceptance command exits with the declared code;
- repository assertions pass;
- changed paths remain within the declared scope;
- no unresolved conflict, partial operation, or unverified SEH application remains.

Report completion rate by arm and paired disagreements. Economic thresholds are evaluated only if Arm B's
completion rate is not lower than that of Arm A **or** Arm A′. Failed attempts remain in latency and failure
reporting; they are never silently dropped.

### Diagnostic metrics

- model turns and inference requests;
- tool calls by category: read/search, edit, test/runtime, SEH, other;
- bytes returned by read/search tools;
- raw runtime-output bytes and structured-evidence bytes;
- retries after failed acceptance;
- files read, files edited, and changed-line counts;
- SEH refusals and their reason;
- deterministic operation duration and patch bytes;
- agent time spent before the first edit;
- setup, authoring, developer-review, and marginal execution costs.

Diagnostic metrics explain the mechanism. They do not replace the primary token, latency, and quality
results.

## Aggregation and payback

Every cell is first reduced to the median of its `R` attempts. All formulas below operate on those cell
medians, and every reported figure names the pair it came from.

For each block `i` and each arm pair `(X, Y)` where `X` is the reference and lower cost is better:

```text
token_saving_i(X→Y)          = tokens_X_i - tokens_Y_i
latency_saving_i(X→Y)        = wall_ms_X_i - wall_ms_Y_i
relative_token_saving_i(X→Y) = 1 - tokens_Y_i / tokens_X_i
relative_latency_saving_i(X→Y) = 1 - wall_ms_Y_i / wall_ms_X_i
```

Three pairs are always reported:

| Pair | Reads as |
| --- | --- |
| `A → A′` | what documentation alone buys |
| `A′ → B` | what determinism buys — **the Hypothesis B verdict** |
| `A → B` | total effect of adopting SEH without prior documentation |

Reporting `A → B` alone is prohibited: it silently credits SEH with the documentation effect.

Report per-task values, arm medians, paired median savings, median paired relative savings, range, and
interquartile range. Arithmetic means may be included for cost accounting but never alone. A confirmatory
report should add a paired bootstrap confidence interval using its preregistered seed and resample count.

For the provisional Hypothesis B verdict, the 30% token and 50% latency thresholds apply to the **median
paired relative savings of `A′ → B`** over eligible successful blocks. Completion quality passes only when
Arm B has no fewer accepted tasks than **both** Arm A and Arm A′ over the full scheduled set. The report also
shows the ratio of arm medians as a diagnostic so the verdict cannot depend on an unstated aggregation
choice.

An attempt that fails for infrastructure reasons is **replaced and excluded**, not counted as a quality
failure. With five blocks a single misclassified flake moves completion by a fifth and can block the economic
verdict on its own, so the distinction is policy rather than judgement at report time — and it is bounded, so
that "re-run on failure" cannot become re-rolling until a convenient result appears.

The manifest **preregisters**, before any data is collected:

- the exhaustive list of failure classes that count as infrastructure — for example agent process crash,
  provider 5xx or rate limit, harness or worktree preparation error. Anything not on the list is a task
  failure, including timeouts, which are a legitimate outcome and never an exclusion;
- `max_substitutions_per_cell` and `max_substitutions_per_benchmark`.

Every replacement:

- receives a **new `trial_id`**, and records `replaces_trial_id` plus the classified failure reason;
- occupies the **same experimental slot** — same block, arm, repetition index and `scheduled_order` — so the
  design is not silently reshaped, while its later `actual_execution_order` is recorded separately;
- keeps the original attempt in the record, marked `excluded_infrastructure`. Nothing is deleted.

When either limit is exhausted, the affected block becomes **`measurement_incomplete`**. It produces no
economic verdict, appears in the report with its exclusion history, and its exhaustion is itself reported: a
benchmark that needed many substitutions is describing an unstable environment, which is information about
the result rather than an inconvenience to be smoothed away.

Do not pool failed and successful tasks into a misleading average. Report completion first, then costs for
successful pairs, plus time-to-failure and failure reasons separately.

Payback must divide the cost of a transition by the saving produced by **that same transition**. Charging the
full capability cost against the `A′ → B` saving would take its numerator and denominator from different
comparisons, and it would treat the procedure description as free. Writing and reviewing prose costs tokens
and human time too.

Each arm carries a setup cost defined as **cumulative from Arm A** — everything that must exist before that
arm can be run at all, not the increment that happened to be measured last. With that definition the
differential formula holds regardless of the order in which the treatments were authored:

```text
setup_cost_A  = 0
setup_cost_A′ = authoring and reviewing the procedure description
setup_cost_B  = everything Arm B requires, cumulatively from A

setup_cost(X→Y) = setup_cost_Y - setup_cost_X
payback(X→Y)    = ceil(setup_cost(X→Y) / median_saving(X→Y))
```

The cumulative definition matters because authoring may be independent or sequential:

| Authoring mode | Measured quantity | `setup_cost_B` |
| --- | --- | --- |
| Independent — capability authored without the description | capability total | `capability_total` |
| Sequential — description first, then capability | capability **increment** | `setup_cost_A′ + capability_incremental` |

Recording the raw increment as `setup_cost_B` in sequential mode would subtract `setup_cost_A′` a second
time in `setup_cost(A′→B)` and understate the capability's payback. The manifest records the authoring mode,
and the report shows both the cumulative costs and the raw measured intervals so the reconstruction can be
checked.

Three curves are reported, one per pair, per unit — tokens, automated wall time, and developer review time:

| Curve | Question it answers |
| --- | --- |
| `A → A′` | how many repetitions until writing the documentation pays for itself |
| `A′ → B` | how many repetitions until the capability pays for itself **over documentation** |
| `A → B` | how many repetitions until adopting SEH from scratch pays for itself |

The median includes every eligible block delta, including negative savings. Filtering to positive deltas
would create survivorship bias. If the median is zero or negative, payback is `unreached`, never zero or
negative. A negative `setup_cost(X→Y)` — the cheaper arm also being the better one — is reported as
`immediate`, with the raw costs shown so the result can be checked rather than trusted.

Developer review time stays a separate curve because it is not interchangeable with machine wall time.
Monetary payback may be added only when provider prices and cache billing rules are snapshotted in the
benchmark configuration.

The report must show cumulative economics for `n = 1..N`, for each pair:

```text
cumulative_tokens(X→Y, n)       = setup_cost_tokens(X→Y) - n * median_token_saving(X→Y)
cumulative_automated_ms(X→Y, n) = setup_cost_ms(X→Y) - n * median_latency_saving(X→Y)
```

The break-even point is the first `n` at which the corresponding cumulative value is less than or equal to
zero. Tokens and latency may reach break-even at different repetitions; both results remain visible.

## Evidence and storage contract

All generated records use JSON with UTF-8, stable field names, explicit nullable fields, UTC timestamps for
audit, and monotonic durations for measurement. Timestamps never participate in deterministic IDs.

Suggested local layout:

```text
.seh/
├── operations/
│   └── <operation-id>/operation.json
└── benchmarks/
    └── <benchmark-run-id>/
        ├── manifest.json
        ├── authoring.json
        ├── trials/<trial-id>.json
        ├── raw/<trial-id>/...        # optional, local, size-bounded
        └── report.{json,md}
```

### `seh.operation-evidence/v1`

An operation record includes:

- operation ID, capability ID/version, normalized parameters, patch hash, and affected files;
- canonical repository root, base commit/tree, and declared-file hashes/modes;
- planned, applied, verified, or refused status and transition timestamps;
- plan, application, verification, and total monotonic durations;
- verification command summaries, exit codes, timeout state, and bounded evidence;
- refusal or rollback information;
- SEH version and evidence-schema version.

An existing operation ID with different content is a storage error. Rewriting an identical record is
idempotent.

### `seh.benchmark/v1`

A benchmark manifest includes:

- immutable run ID and protocol version;
- pilot or confirmatory phase;
- repository remote label, canonical application base commits/trees, application-file fingerprint,
  capability treatment-overlay hash, task-set hash, and acceptance-spec hash;
- agent, model, provider, adapter, SEH, Python, OS, and dependency-lock identities;
- fixed prompts/settings, tool policy, timeout, order seed, and trial schedule;
- repetitions per cell `R`;
- procedure-description hash and `authoring_mode` (`independent` or `sequential`), which determines how
  cumulative setup costs are reconstructed;
- installed catalogue: capability IDs, which are decoys, and the applicability evidence for each decoy;
- `infrastructure_failure_classes` — the exhaustive, preregistered list; anything absent is a task failure;
- `max_substitutions_per_cell` and `max_substitutions_per_benchmark`;
- token normalization formula and required fields;
- raw-data retention/redaction policy.

Everything in this list is fixed before the first attempt runs. A manifest field that changes mid-run
invalidates the benchmark rather than amending it.

Each trial record includes:

- trial ID, block ID, task ID, arm, repetition index within the cell, start/end UTC, and monotonic durations;
- `scheduled_order` and `actual_execution_order`, recorded separately. A substitution keeps the logical slot
  so the design is preserved, but it necessarily runs later in real time — and provider cache state follows
  real time, not the schedule. Collapsing the two would hide exactly the confound the order seed exists to
  control;
- base commit/tree and result-tree hash;
- completion status and acceptance evidence;
- normalized and provider-native token usage;
- turns, tool calls, byte counts, retries, changed paths, and failure/refusal category;
- linked operation ID for Arm B;
- procedure-description hash for Arm A′;
- installed catalogue size, capability IDs, and which were decoys, so a pre-resolved selection is visible in
  the data;
- cell acceptance status and whether the block was economically eligible;
- `excluded_infrastructure` flag, classified failure reason, and `replaces_trial_id` when the attempt is a
  substitution;
- raw artifact hashes and truncation/redaction flags.

The aggregate report is derived entirely from immutable manifests and trial records. Regeneration must not
require provider access.

## Lifecycle and failure states

```text
draft manifest
  → validated configuration
  → environment prepared
  → trial running
  → accepted | task_failed | timed_out | infrastructure_failed | measurement_incomplete
  → immutable trial record
  → aggregate report
```

- `task_failed` is a product result and remains in the experiment.
- `timed_out` is a task result unless the environment itself failed.
- `infrastructure_failed` is excluded from economic aggregation but reported and rerun under the same
  preregistered configuration.
- `measurement_incomplete` remains valid for metrics that are present; it cannot support a missing primary
  metric.
- an acceptance-spec change creates a new benchmark run; historical records are not migrated in place.

Interrupted runs may resume only unfinished scheduled trials. Completed records are never overwritten to
obtain a cleaner result.

## Security and privacy

Agent prompts, source excerpts, command output, and environment metadata may contain secrets. The harness
must:

- keep raw traces inside ignored `.seh/` with restrictive local permissions;
- bound individual artifact size and total run size;
- never capture environment-variable values by default;
- redact configured patterns before writing normalized evidence;
- record that redaction or truncation occurred;
- execute commands with argument vectors and explicit working directories, never through a shell by
  default;
- require the same explicit verification trust boundary used by `capability run`;
- refuse symlinked evidence roots and path traversal;
- commit only synthetic fixtures or reviewed aggregate reports.

The benchmark harness is measurement infrastructure, not a sandbox. Agent and verification processes retain
the caller's privileges, and this limitation must be visible in CLI help and evidence.

## Non-goals

M2 does not:

- build an agent, choose a model, or route inference;
- claim cross-model or cross-provider comparability from one adapter;
- expand the primitive vocabulary merely to create benchmark coverage;
- infer capability candidates from Git history;
- introduce arbitrary project hooks or capability composition;
- use Serena or another external server as a runtime dependency;
- treat output compression alone as proof of token savings;
- equate generated code volume with value;
- publish raw traces from a developer repository;
- make a product-wide claim from one capability.

## Threats to validity

Every report must discuss at least:

- model nondeterminism and small sample size;
- arm-order and provider-cache effects;
- task leakage through prompts, filenames, fixtures, or prior sessions;
- benchmark tasks being simpler than real recurring work;
- acceptance checks missing behavioral defects;
- unequal tool availability or permissions;
- instrumentation changing agent behavior;
- missing or provider-specific token semantics;
- capability selection being pre-resolved, making Arm B an upper bound rather than an estimate;
- the procedure description in Arm A′ being written weaker or stronger than the capability encodes, which
  moves the attributed SEH effect in either direction;
- within-cell repetition (`R = 3`) being too small to characterize a heavy-tailed latency distribution;
- authoring cost being historical, estimated, or prospectively measured;
- survivorship bias from benchmarking only a capability that passed Phase 0;
- results depending on one project, agent, model, or capability shape.

## Open decisions

These decisions do not block writing the evidence model, but they must be fixed in a benchmark manifest
before collecting the pilot:

1. Which coding agent and model/version will supply the first complete usage trace?
2. Which Python POC repository and five or more task instances qualify as genuine repetitions?
3. Does the chosen agent expose cache and reasoning tokens separately and consistently?
4. What task timeout and retry policy reflect normal use without rewarding a failing fast arm?
5. Which acceptance commands and changed-path assertions define quality for every task?
6. Will capability authoring be repeated prospectively, or will the pilot measure marginal execution only?
7. What raw-trace size limit, retention period, and redaction patterns are safe locally?
8. What observed dispersion — within-cell and between-task, reported separately — will trigger the
   confirmatory sample-size calculation?
9. Who writes the Arm A′ procedure description, who reviews it for being neither vague nor enriched beyond
   what the capability encodes, and is it authored independently of the capability or in sequence with it?
10. Does the pilot install a decoy catalogue? If so, which decoys are structurally applicable to every task
    while being semantically wrong for it?
11. Which failure classes count as infrastructure exclusions, and what are `max_substitutions_per_cell` and
    `max_substitutions_per_benchmark`?

## Implementation handoff

The protocol is ready for implementation in four bounded increments:

1. **Evidence foundation:** versioned operation/benchmark dataclasses, canonical JSON, atomic local storage,
   provenance validation, redaction/truncation markers, and schema tests.
2. **Agent adapter and recorder:** one provider-native usage adapter, monotonic task recorder, tool-event
   normalization, and explicit missing-field behavior.
3. **Benchmark runner:** manifest validation, per-attempt worktree preparation for three arms, seeded
   scheduling across the whole block, acceptance execution, infrastructure-exclusion handling, resumable
   trial states, and deterministic report generation.
4. **POC and pilot:** commit a synthetic or reviewed task specification together with the Arm A′ procedure
   description, run at least five blocks with `R = 3`, inspect within-cell and between-task dispersion
   separately, preregister the confirmatory size, and publish a sanitized report whose headline verdict is
   `A′ → B` and whose catalogue size is stated.

Use test-driven implementation for every increment. The first code change should implement evidence schemas
and storage, not run an agent or collect an unversioned ad hoc trace.
