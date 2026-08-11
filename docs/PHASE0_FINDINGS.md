# Phase 0 Findings

Status: **initial spike complete; Phase 0 and the thesis gate remain open.** Specification in
[`CAPABILITY_MODEL.md`](CAPABILITY_MODEL.md).

Phase 0 hand-authored three capabilities of different shapes and ran them over real source files in this
repository. The spike is read-only: it never wrote to the working tree.

The evidence below is reproducible. The distilled experiment — primitives, capabilities, captured fixtures
and the findings as executable assertions — lives in
[`experiments/phase0/`](../experiments/phase0/README.md) and runs with `pytest experiments/phase0`. It sits
outside the runtime and outside the product test suite, so an experiment can never gate the build.

## Capabilities chosen

| Capability | Real occurrences | Shape |
| --- | --- | --- |
| `add-cli-command` | 4 (`init`, `index`, `inspect`, `neighbors`) | module-level function insertion + statement-group insertion inside a function body |
| `add-node-kind` | 11 `NodeKind` members, 4 `TYPE_NODES` entries | class-body member insertion + collection-literal entry |
| `add-java-relation-kind` | 2 (`extends`, `implements`) | class-body member insertion + method-local collection-literal entries |

One candidate was **rejected before implementation**. `add-graph-query` (3 occurrences in `GraphStore`)
requires the SQL body as a parameter, which is a model-generated code slot — forbidden for closed MVP
capabilities. The selection criteria caught it without any code being written.

## Initial two-capability result

**Only one effect primitive was shared between the two capabilities.**

| Primitive | `add-cli-command` | `add-node-kind` | Status |
| --- | --- | --- | --- |
| `splice.after` | ✓ | ✓ | **shared** |
| `python.symbol` (last-with-prefix) | ✓ | — | refined: needed a selector, not just a name |
| `python.statement` (return in function) | ✓ | — | **added** — not in the proposed vocabulary |
| `splice.before` | ✓ | — | added, with a declared escape hatch (see F5) |
| `python.class_body` | — | ✓ | **added** — not in the proposed vocabulary |
| `python.collection_literal` | — | ✓ | as proposed |
| `splice.into_collection` | — | ✓ | as proposed |
| `python.module` | — | — | **unexercised** |
| `python.import_block` | — | — | **unexercised** |
| `file.render` | — | — | **excluded provisionally** — no real recurring event creates a file |
| `verify.command` | — | — | unexercised as a primitive; verification was run ad hoc |

Two capabilities produced eight primitives with an overlap of one. That is a weak signal for a reusable
algebra. Three readings are possible, and Phase 0 cannot yet distinguish between them:

1. the vocabulary is too fine-grained and the real primitives are coarser;
2. two capabilities is genuinely too small a sample;
3. the two chosen shapes were too dissimilar to share anything but the most generic effect.

The third, shape-adjacent capability subsequently discriminated between (2) and (3): it reused all four
predicted primitives. See F7. Phase 0 nevertheless remains open because F8 and F9 invalidated the evidence
used for fidelity and procedural recurrence.

## What was proven

**F1 — Source preservation works.** Every touched file was insert-only, with every pre-existing line
byte-identical:

| File | Bytes | Pre-existing lines kept | Lines removed |
| --- | --- | --- | --- |
| `src/seh/cli.py` | 5743 → 5987 | 165/165 (100%) | 0 |
| `src/seh/models.py` | 1448 → 1478 | 75/75 (100%) | 0 |
| `src/seh/java_adapter.py` | 7994 → 8050 | 233/233 (100%) | 0 |

**F2 — The generated scaffolding actually runs.** The patched package was imported in an isolated copy:
`seh report` parses, dispatches to `cmd_report`, raises `NotImplementedError` as scaffolded, and the
pre-existing `inspect` command still works.

**F3 — Idempotency and safe refusal hold.** All three capabilities refuse a second application. Refusal was
demonstrated in two distinct failure modes: a missing anchor, and a *wrong syntactic form* —
`TYPE_NODES = dict(a=1)` is rejected because `splice.into_collection` declares support for dict/list/set
literals only and does not adapt to a call expression.

## What was not proven

**Gate 1 (fidelity) did not run against a genuine pre-implementation fixture.** The attempted fixture for
the third capability was created by subtraction from the current snapshot. F9 shows why that state was
synthetic and the resulting comparison invalid.

**Gate 2 (generalization) was run once per capability, not twice.** Each capability was instantiated with a
single parameter set; the second, developer-approved case is still missing.

## Findings that change the model

**F4 — Style derivation must be scoped to siblings, not to adjacent whitespace.**

This surfaced as a real defect during the spike. The first implementation measured the whitespace
immediately *following* the anchor. That is correct for a middle child and wrong for a last child, where the
trailing gap belongs to the enclosing scope: inserting after the last `NodeKind` member reproduced the
*inter-class* gap and emitted three blank lines inside the enum.

The correct rule is to measure the gap between two existing siblings of the same parent. This makes style
derivation the **locator's** responsibility rather than the effect's — only the locator knows what the
siblings are. `Span` therefore carries a `separator` measured at location time.

**F5 — Horizontal style derives cleanly; conventional groupings do not.**

`splice.into_collection` derived indentation and the trailing-comma convention from its neighbours with no
configuration, producing output indistinguishable from hand-written code. But the argparse registration
"block" is *three sibling statements that humans read as one unit*. The AST exposes no boundary for it, so
its vertical lead cannot be derived and must be declared by the capability.

This is a real limit of AST-derived style: it covers horizontal rhythm and sibling-level vertical rhythm,
but not conventional groupings that the grammar does not model.

**F6 — Capabilities scaffold structure; they do not author behaviour.**

`cmd_inspect`'s body is domain logic. A closed capability cannot produce it and must not try. The capability
emits a well-formed skeleton that imports, dispatches, and fails loudly (`NotImplementedError`); the agent
then writes the behaviour as ordinary work.

This is consistent with the thesis — IntelliJ's "Generate →" produced structure, not behaviour — but it
changes gate 1: **fidelity can only compare the structural subset of an accepted change, never the whole
change.** In practice, capture must split the accepted work into the scaffolding a capability reproduces and
the domain logic that stays manual; the fidelity fixture is the former.

`CAPABILITY_MODEL.md` now scopes fidelity to that accepted structural subset and separates later domain
behaviour from the deterministic scaffold.

The first real capture makes that boundary auditable rather than implicit. It preserves the complete
accepted diff as `accepted.patch`, the replayed structural diff as `expected.patch`, and the human rationale
as `scope.yaml`; validation mechanically requires every expected hunk to occur exactly in the accepted patch
for the same file. For `install`, the recurring scaffold is two thin local-import adapters, while parser
details and command behavior live in a command-specific module excluded explicitly from fidelity.

## Third capability: executed, with a decisive result

Gates 3 and 4 passed. Gate 1 **failed**, and the failure invalidates the way all three capabilities were
selected — not the mechanism they are built on.

### F7 — Primitive reuse confirmed (the positive result)

`add-java-relation-kind` reused every predicted primitive: `python.class_body`, `python.collection_literal`,
`splice.after`, `splice.into_collection`. Reaching a dictionary local to `JavaAdapter._type_relations`
required only generalizing how the locator is *addressed* — a dotted scope path
(`JavaAdapter._type_relations.wrappers`) instead of a module-level name. That is a refinement of one
primitive, not a new one.

Overlap therefore moved from one shared primitive to four. The weak first signal was an artefact of choosing
two dissimilar shapes, not evidence that the algebra fails to generalize.

The capability also needed `syntax_nodes` to be a **list**: `EXTENDS` maps two Java syntax nodes
(`superclass`, `extends_interfaces`) while `IMPLEMENTS` maps one. A capability hard-coded to a single entry
would have passed one case and failed the other.

### F8 — Textual multiplicity is not procedural recurrence

Reconstructing each capability's history exposed the problem:

| Capability | Occurrences in current code | Incremental events in history |
| --- | --- | --- |
| `add-cli-command` | 4 | **0** — all four handlers appeared in the bootstrap commit |
| `add-java-relation-kind` | 2 | **0** — all seven `EdgeKind` members appeared together |
| `add-node-kind` | 11 | **1** — and that event added three members at once |

None of the three procedures was ever performed repeatedly. They were selected by counting structures in a
snapshot, and a snapshot cannot distinguish *written once as a batch* from *added N times incrementally*.

`CAPABILITY_MODEL.md` grounds granularity in "a stable pattern of that project", and this spike read that as
multiplicity in the current tree. The criterion must instead be **repeated events in history**: a capability
is justified by a procedure someone actually performed more than once.

### F9 — A fidelity fixture cannot be reconstructed by subtraction

Gate 1 was attempted by deleting `EXTENDS` and its two wrapper entries from the current files. Replay then
appended them at the end, producing a result that is semantically identical and textually different:

```text
accepted            replayed
DECLARES            DECLARES
EXTENDS       ←     IMPLEMENTS
IMPLEMENTS          ...
...                 EXTENDS     ←  appended at the tail
```

Subtracting from the present produces a state that never existed. Member order in an enum or dictionary is a
record of the order in which things were historically added, so an append-style capability can only
reproduce an accepted patch when the fixture is the true pre-change state.

The consequence is a product constraint, not a spike inconvenience: **the true baseline must be recorded
before the change.** The fixture may be materialized after developer acceptance from that baseline and the
resulting diff, but it cannot be mined later from an unproven snapshot. This directly limits the M5 item
"derive candidate capabilities from past commits" — it depends on a real parent tree that squash and rebase
routinely destroy.

### Why repository history cannot finish gate 1

SEH's own history is a poor retrospective Phase 0 subject: it is small and was largely written in a single
bootstrap commit, so no capability here has an accepted incremental patch to reproduce retrospectively. This
is a property of the subject, not of the model; a forward capture can still use this repository.

## Prospective rehearsal

A read-only rehearsal then exercised that forward flow against the real current bytes of `src/seh/cli.py`.
The `before` state was captured first (`sha256:a0877351bb7253b995fb1a46d7bf9ce7798408d25aff6a28f13abe22c5cd8b60`).
An ordinary, independently authored structural edit added a proposed `report` command in memory. It used
direct literal insertions at explicit text boundaries and did not call the capability's AST locators, splice
effects, or template constants. Replaying `add-cli-command` from the captured bytes produced the same bytes
exactly.

The evolved in-memory state was then used for a second proposed event, `doctor`. Independent edit and replay
again matched byte-for-byte. Both generated modules parsed and imported, and both parser registrations
resolved to the expected handler. Idempotency and safe refusal also passed. The repository source was never
written.

This is positive evidence for the capture mechanics, but it does **not** close gates 1–2 as product gates:
neither proposed command was retained as a real project change, and the developer has not yet approved or
edited `doctor` as the generalization case. The rehearsal therefore turns the remaining blocker from a
technical unknown into an explicit product decision.

## Phase 0 closing sequence

The retained events will be the capability command group already required by the roadmap, not commands
invented for the experiment:

1. Implement `seh capability validate` manually. It creates both the parent group and its first subcommand,
   so it is one-time setup and **not** a clean capture event.
2. Start again from a recorded clean Git baseline, implement `seh capability install` manually, accept it,
   and capture this first clean `add-capability-subcommand` event.
3. Derive `add-capability-subcommand` from the accepted structural subset of `install`.
4. Use the already implemented `validate` command to run the candidate's four gates.
5. With explicit developer approval, generate `seh capability run` as the second clean event and gate 2.

The apparent self-reference in step 4 is not circularity. `validate` is runtime machinery implemented by
hand; `add-capability-subcommand` is project data being judged by that machinery.

The capture source is Git, not a continuous edit ledger. Every eligible task records a clean worktree and
baseline tree before mutation. Once the developer confirms capture, the fixture is materialized from that
baseline and the accepted diff. If the task began dirty or no baseline evidence exists, capture refuses
rather than guessing which bytes predated the task.

`file.render` is removed from the provisional algebra. None of the real retained events creates a file, and
adding a file solely to exercise the primitive would fabricate evidence. It can be admitted later when a
genuinely recurring procedure requires file creation.

### Closing checklist

Phase 0 closes only when all of these are true:

- [x] `validate` exists as the manually implemented group-creation event and is not used as fidelity data;
- [ ] `install` starts from a recorded clean Git baseline and is accepted as a real project change;
- [ ] the captured expected patch declares only the accepted structural subset of `install`;
- [ ] `add-capability-subcommand` reproduces that subset byte-for-byte;
- [ ] the developer approves or edits `run` before it becomes the generalization case;
- [ ] `run` passes generalization and both retained cases pass idempotency and safe refusal;
- [ ] no provisional primitive exists solely because the experiment needed coverage.

The model corrections are now applied: granularity requires repeated *events*, fixtures are captured at
change time from a recorded clean Git baseline, and fidelity is scoped to the accepted structural subset.

The economic hypothesis remains untouched and untested; nothing here speaks to payback.
