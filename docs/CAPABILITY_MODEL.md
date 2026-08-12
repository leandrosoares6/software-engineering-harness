# SEH Capability Model

## Purpose

SEH learns the recurring engineering procedures of a project as versioned capabilities. This document
defines the unit of learning, the deterministic vocabulary used to express it, and the mechanics that make
source-preserving replay possible.

The model has three levels:

```text
primitive
    ↓ composed into
capability
    ↓ instantiated with parameters as
operation
```

- A **primitive** is a small, project-agnostic deterministic instruction implemented by SEH.
- A **capability** is a versioned, project-specific procedure composed from primitives, templates, contracts,
  and examples.
- An **operation** is one immutable invocation of a capability against a compatible base state. It produces a
  plan, patch, verification result, and evidence.

The versioned artifact is therefore a capability, not an operation. Capabilities live in
`.seh-capabilities/`; operation records are runtime evidence and remain in local `.seh/` state.

## Granularity

A capability begins where a decision ends and ends where another decision begins.

Too small:

```text
insert-import
create-file
append-to-list
```

Those are primitives. They manipulate code but contain no knowledge of how a particular project works.

Too large:

```text
implement-billing-module
redesign-agent-memory
migrate-to-event-driven-architecture
```

Those requests contain domain or architectural decisions that cannot be reduced safely to typed parameters.

Appropriate capability boundaries look like:

```text
add-agent-tool
add-authenticated-route
add-knowledge-source
add-event-consumer
add-agent-evaluation-case
```

A candidate has suitable granularity when:

1. it represents one recognizable engineering intent;
2. the procedure occurs as repeated **change events**, not merely as multiple similar structures in one
   repository snapshot;
3. it coordinates more than a trivial textual edit;
4. its variation is expressible through typed parameters;
5. its effects are bounded and known before writing;
6. correctness is objectively verifiable;
7. replay requires no new architectural or domain decision.

Snapshot multiplicity is not evidence of procedural recurrence. Four commands may have been authored once
in a bootstrap commit; eleven enum members may have arrived in one batch. Retrospective candidates require
distinct accepted change events in history. A prospective capture must preserve the actual `before/` bytes
at the time of the first change and exercise a second event before clearing the thesis gate.

## Closed capabilities in the MVP

MVP capabilities are **closed**: every variation required for replay must fit in declared, typed parameters.
They do not accept model-generated source-code slots or callbacks.

Two parameter types are admitted. The second rests on weaker evidence than this model's own admission rule
requires, and the threat below states that plainly rather than leaving it to be inferred from the argument.

| type | carries | refuses |
| --- | --- | --- |
| `python_identifier` | a name Python itself constrains | non-identifiers and keywords |
| `text_line` | one line of prose inside otherwise mechanical wiring | quotes, backslashes, control characters, template expressions, surrounding whitespace, over 200 characters |

`text_line` exists because of a measured dead end. The POC capability's accepted change was seven-eighths
derivable from a single identifier and blocked entirely by one fragment: `help="show status"`. Only three
outcomes were available, and two were unacceptable. Narrowing the structural claim — which can only drop whole
hunks — would have dropped the registration hunk and with it all the wiring, leaving a capability that adds a
function nobody calls. Adjusting the fixture to match what the templates produce is exactly the fabrication the
provenance anchors now refuse. So either the residue became expressible, or the procedure was not capturable at
all.

The distinction that keeps this consistent with rejecting free-form arguments: **this prose is not structure, it
is a hole in the structure.** A `text_line` does not let SEH invent text; it lets the agent supply the one
editorial fragment the procedure genuinely varies by, which is the intended division of labour. What was
rejected, and stays rejected, is passing code, argument lists or callbacks as parameters.

It refuses rather than escapes, and that is deliberate. A value is spliced into source verbatim, so the template
must stay a literal picture of the emitted bytes; if SEH quoted values itself, a reviewer comparing a template
against a patch could no longer see where the quotes came from. The cost is real and accepted: an apostrophe in
help text is a refusal, not a transformation. Prose that cannot survive that is behaviour, and belongs in a
module the capability never touches.

#### Declared threat: `text_line` was admitted on a single non-recurring occurrence

Recorded 2026-08-12, at the time of admission rather than afterwards.

The rule this model states for the primitive vocabulary is that something is admitted when **a real recurring
procedure demands it — not to round out a vocabulary**. `text_line` does not meet that rule, and the argument
above, read alone, reads stronger than the evidence underneath it.

| | |
| --- | --- |
| Occurrences demanding it | one |
| Recurrence observed | none |
| Where | a POC written to exercise SEH, not a project doing its own work — commits in [`experiments/poc-utilidade/EVIDENCE.md`](../experiments/poc-utilidade/EVIDENCE.md) |
| The procedure it unblocked | adding a CLI command whose entire body is `print("<name>")` |
| Checked against the north-star capability | no — whether `add-agent-tool` needs a text field was never established |

The reasoning was sound given the goal of making that capability honest, but the goal itself was shaped by the
POC. A capability whose commands have no behaviour is a high wiring ratio over an empty denominator: it can
neither confirm nor refute that the type is needed by work anyone would do anyway. This is the near neighbour of
the finding already recorded twice in [`PHASE0_FINDINGS.md`](PHASE0_FINDINGS.md) — multiplicity in a snapshot is
not recurrence, and structure in a snapshot is not structure the project intends to keep.

**Resolution condition.** `text_line` is confirmed when a procedure that recurs in a repository doing its own
work requires it, and that occurrence is recorded here. If the first such procedure does not require it, the
type is removed rather than retained on the strength of already existing. Being implemented, tested and
documented is not evidence; it is only sunk cost, and this section exists so that cost cannot quietly become the
justification.

Nothing built on `text_line` may be cited as evidence for it. In particular, the POC capability now passing four
gates is a consequence of the admission, not support for it.

An extension point would make two invocations of the same capability incur different inference cost depending
on how the slot was filled. That is incompatible with the MVP measurement protocol, even though SEH itself
would not call the model. If extension-bearing capabilities are ever introduced, they must be a separate
category with a separate economic baseline.

Capabilities also cannot invoke other capabilities in the MVP. They compose only versioned SEH primitives.
Capability-to-capability composition is deferred because it introduces dependency versions, cycles, parameter
propagation, effect conflicts, and distributed rollback.

### Structural scope versus behavior

A closed capability guarantees that **its own patch** is completely determined by declared parameters. It
does not guarantee that the capability completes the developer's entire feature without further reasoning.

Capabilities scaffold structure and wire existing symbols; they do not invent new domain behavior. For
example, `add-cli-command` can create a command skeleton, register its parser and dispatch, and make the
skeleton fail loudly with `NotImplementedError`. The external agent may then implement the command body as a
separate, ordinary edit. That edit is not a hidden extension point, is not part of the capability operation,
and must be measured separately.

This distinction narrows fidelity: the accepted reference is the **structural subset** the capability claims
to reproduce, not every behavioral line in the original feature. Capture must make that boundary explicit in
the expected patch; SEH never infers it.

## A closed primitive algebra

The primitive vocabulary is closed and deliberately small. A consuming project cannot add arbitrary Python
plugins or lifecycle scripts as new primitives. If two real capabilities require a missing primitive, that is
product evidence: the primitive can be added to SEH deliberately, versioned, reviewed, and tested.

The admitted vocabulary is exactly what the one retained capability required:

```text
LOCATORS (Python AST → source span)    EFFECTS (source text → patch)
├── python.symbol                     ├── splice.before
└── python.statement                  └── splice.after

VERIFICATION
└── verify.command
```

That is the whole algebra, and it matches `SUPPORTED_STEPS` in the runtime exactly. It is small because
nothing else has been demanded by a real, prospectively captured, developer-accepted change event.

`python.module`, `python.assignment`, `python.class_body`, `python.collection_literal`,
`python.import_block`, `splice.into_collection`, and `file.render` were proposed at various points and are
**not admitted**. Some were never exercised. Others were exercised only against the Java adapter the project
has since removed, which leaves those claims without evidence rather than with weak evidence — a documented
primitive with no implementation and no proof is worse than an absent one.

A primitive is admitted when a real recurring procedure demands it — not to round out a vocabulary, and not
to restore a deleted experiment. Creating a module merely to cover `file.render` would repeat the
snapshot-multiplicity error in a new form. See [`PHASE0_FINDINGS.md`](PHASE0_FINDINGS.md).

The parameter vocabulary is held to the same standard, and one entry currently fails it: `text_line` was
admitted on a single non-recurring occurrence, under a declared threat with a resolution condition. A reader
applying this rule should know the exception exists rather than discover it later.

`src/seh/source_edit.py` is the sole implementation and the normative authority. `experiments/phase0/`
preserves the prospective `install` → `run` capture that closed the technical gate; it holds fixtures and
executable checks, not a second algebra.

An earlier spike explored a wider vocabulary against the Java adapter. That adapter was removed when the
project became Python-only, and its evidence went with it. The lessons it produced are retained above and in
`PHASE0_FINDINGS.md` — style derives from siblings, capture cannot be reconstructed by subtraction — but the
primitives it exercised are not, because a claim whose proof was deleted is a claim without proof.

The first retained event also defines a deliberately narrow command seam. New `capability` subcommands add
two local-import adapters in `capability_cli.py`: `cmd_<name>` delegates to
`capability_<name>.execute`, and the parent parser delegates to `capability_<name>.configure_parser`.
Command-specific help, arguments, behavior, and presentation remain in that module. This module-per-command
boundary is useful without capability capture once command bodies grow, and it lets the recurring wiring vary
only by a validated Python identifier instead of accepting prose, argument lists, or arbitrary source as
parameters. `cmd_validate` remains inline until after the `install` fixture is captured so a retrospective
refactor cannot contaminate the first real event.

Each structural primitive supports one declared syntactic form and refuses the others. `python.statement`
locates the top-level `return` of a named function; it does not locate "wherever this value should go". If a
future capability needs to register a value in a collection, a list literal, set literal, dictionary,
`.extend()` call, decorator registry, and annotation-based registry are different forms, each requiring
explicit support or explicit refusal — never adaptation.

## Source-preserving Python edits

Python's stdlib `ast` is a locator, not a source rewriter. A parse/unparse round trip changes source even when
the tree is untouched: comments disappear and quote style, blank lines, and collection formatting may change.
Consequently, mutation must never use `ast.unparse()`.

The supported mechanism is:

```text
Python AST → locate and validate a structural anchor → exact source offset
source text + rendered fragment → splice at that offset → patch
```

The AST provides node positions (`lineno`, `col_offset`, `end_lineno`, `end_col_offset`). SEH converts the
validated source span into an insertion offset and changes only the declared fragment. Untouched files remain
byte-identical; within a touched file, bytes outside the splice remain identical.

Inserted text derives local style from structurally relevant siblings, including indentation, separators,
and trailing commas. Style derivation belongs to the locator: only it knows the parent and sibling set. A
located span therefore carries the separator measured between two existing siblings of the same parent; an
effect applies that separator but does not infer it from arbitrary adjacent whitespace.

Grammar does not represent every human grouping. A group of adjacent argparse statements, for example, has
no AST boundary. Horizontal style and sibling rhythm are derived; conventional grouping outside the grammar
must be declared explicitly by the capability. SEH must not impose a formatter-specific style during replay.
Formatting tools may be verification commands, but they are not a hidden prerequisite for fidelity.

Every effect contributes to an in-memory plan. SEH validates all preconditions and detects conflicting
effects before writing. The complete patch is applied atomically; a failed precondition or verification must
not leave a partial structural edit.

## Capability package

A capability candidate is an agent-authored package such as:

```text
.seh-capabilities/
└── add-capability-subcommand/
    ├── capability.yaml
    ├── templates/
    │   ├── handler.py.tmpl
    │   └── parser-registration.py.tmpl
    └── examples/
        ├── fidelity/
        │   ├── before/
        │   ├── case.yaml
        │   ├── accepted.patch
        │   ├── expected.patch
        │   └── scope.yaml
        ├── generalization/
        │   ├── before/
        │   ├── case.yaml
        │   ├── accepted.patch
        │   ├── expected.patch
        │   └── scope.yaml
        └── refusal/
            ├── before/
            └── case.yaml
```

The hand-built validator uses the deliberately restricted schema
`seh.capability.phase0/v0.1`. It is evidence for the runtime mechanics, not the final
`seh.capability/v0.1` public format. The current manifest is:

```yaml
schema: seh.capability.phase0/v0.1
id: seh.add-capability-subcommand
version: 1

parameters:
  name:
    type: python_identifier

preconditions:
  - uses: text.absent
    with:
      file: src/seh/capability_cli.py
      value: "def cmd_{{ name }}("

steps:
  - uses: splice.after
    with:
      file: src/seh/capability_cli.py
      locator: python.symbol
      selector: last_function_with_prefix
      prefix: cmd_
      template: templates/handler.py.tmpl
  - uses: splice.before
    with:
      file: src/seh/capability_cli.py
      locator: python.statement
      function: configure_capability_parser
      statement: return
      lead: "\n"
      template: templates/parser-registration.py.tmpl

verification:
  - uses: verify.command
    with:
      executable: pytest
      args:
        - tests/test_capability.py
      timeout_seconds: 30
      expected_exit: 0
```

`case.yaml` supplies typed parameters; the generalization case additionally requires `approved: true`.
Idempotency reuses the fidelity fixture and applies the same candidate twice. Arbitrary `before` and `after`
hooks are excluded. Verification has an explicit executable, argument vector, timeout, and expected exit
status; it runs with `shell=False` inside a temporary fixture copy. Manifest, template, and fixture paths are
size-limited and confined against traversal. Fixture enumeration applies its file limit incrementally and
rejects every symlink instead of following it.

The temporary copy protects the working tree from the structural plan; it is not an operating-system
sandbox for `verify.command`. A verification executable can still access whatever the invoking user can
access. `validate` therefore refuses to execute commands by default. The developer must first review the
candidate locally and then pass `--allow-verification`; this flag is an explicit trust decision, not a
sandbox. Team review of an installed capability in a later PR is a separate boundary and cannot replace the
pre-execution review. Future sandboxing must not be implied by the current implementation.

## Base-state fixtures and the four gates

A candidate is usually authored after the accepted implementation exists, so fidelity cannot run against the
current working tree: the created artifacts are already present. SEH therefore requires a **recorded clean
Git baseline** at task start: the worktree has no tracked or untracked changes, and the baseline tree or
unborn empty tree is recorded before mutation. After developer confirmation, declared `before` bytes come
from that baseline and the accepted structural subset comes from its diff.

This resolves the timing problem without a resident edit ledger or a capture decision before the developer
has seen working code. Recording a Git tree is cheap and unconditional; deciding whether to crystallize the
successful procedure still happens afterward. If the baseline was dirty, absent, or cannot be proven, SEH
refuses capture because the true boundary between pre-existing work and the new change is unknowable.

Fixtures must never be reconstructed later by deleting lines from the final snapshot: ordering and
neighboring structure are historical facts, and subtraction can create a state that never existed.

Each expected case preserves three distinct capture artifacts. `accepted.patch` is the complete accepted
change, `expected.patch` is the structural subset claimed by the capability, and `scope.yaml` records the
baseline plus human-readable inclusion and exclusion reasons. The rationale remains reviewable prose, but
the containment claim is executable: validation requires every unified-diff hunk from `expected.patch` to
occur in `accepted.patch` with the same file, ranges, and body. Only Git's optional section label after the
second `@@` is normalized because the runtime renderer does not emit it. Missing artifacts, malformed scope
YAML, or a hunk not present in the accepted change fail closed.

**Containment alone is a closed loop, and it once let a dishonest package through.** Both patches are
author-supplied text checked only against each other, so editing them together — to make a fixture fit a
limitation of the templates — satisfied every gate while the package claimed a change the developer had
never accepted. `scope.yaml` named the two commits that would have exposed it, and nothing read them. Two
anchors outside the package now close that loop:

- **Recorded digests.** `scope.yaml` carries `artifacts.accepted_patch_sha256` and
  `artifacts.expected_patch_sha256`, written when the patches were generated. A patch edited without its
  record fails to load. This anchor travels inside the package and needs no repository, but it is a
  consistency anchor rather than a security boundary: whoever edits the patch can edit the digest.
- **Recomputation from history.** Every line `expected.patch` adds must be present in the declared file at
  the accepted commit, and every line it removes must have been present at the baseline. This is the check a
  self-consistent forgery cannot survive. It compares content rather than rendered bytes, because hunk
  offsets and `/dev/null` headers are renderer-dependent, and a byte comparison would fail honest packages
  while catching no fabrication.

Provenance is reported as `verified`, `unreachable` or `not_declared` on every `validate` and `install`, and
a contradiction refuses the package before any gate runs — there is nothing worth measuring against a
fabricated reference. `unreachable` is a legitimate outcome, since a rebase, a squash merge, a shallow clone
or a package copied out of its origin repository all destroy reachability without implying dishonesty; it is
printed precisely so a digest-only package can never be mistaken for a history-verified one. A `commit` value
that is present but unreadable — an all-digit revision, which YAML parses as an integer — is an error rather
than a silent downgrade to `not_declared`.

The limitation this closes must be stated the other way round too: when a capability cannot express part of
an accepted change, that part belongs under `excluded` with a reason. Adjusting a patch to match what the
templates happen to produce is the failure, not the workaround.

The captured bytes become scoped fixtures of declared files, not long-lived Git references. The fixture
survives later rebases and squash merges because it stores the real state directly. It contains only the
minimum state needed to exercise the capability.

After local review, `seh capability validate --allow-verification` runs four gates:

1. **Fidelity** — instantiate the candidate against the first `before/` fixture and reproduce the accepted
   **structural patch** over declared files. Behavioral edits outside the capability boundary are excluded
   explicitly, never silently ignored.
2. **Generalization** — instantiate it against a different fixture and parameter set proposed by the agent
   and approved or edited by the developer.
3. **Idempotency** — run it over its own result; the second invocation is a no-op or an explicit
   already-applied refusal, never a duplicate edit.
4. **Safe refusal** — run it against an incompatible fixture; it must reject before writing anything.

Only a candidate that clears all four can be promoted by `seh capability install`. Installation first takes
a bounded, byte-exact snapshot of regular candidate files, stages it inside ignored local `.seh/` state,
revalidates that snapshot, and rejects any change to it during verification. It then promotes the directory
atomically to `.seh-capabilities/<capability-id>` under the canonical Git root. Symlinks, special files, concurrent
installation, and replacement of an existing capability are refused; a failed gate or promotion leaves no
partial catalogue entry.

## Replay contract

The deterministic contract is:

```text
capability + parameters + compatible base state → same operation plan and patch
```

Compatibility uses local preconditions: expected symbols, exact anchor kind, relevant structural-fragment
hash, artifact absence, and supported capability schema. Unrelated repository changes do not invalidate the
capability.

`seh capability run CAPABILITY_ID ...` instantiates an operation. The operation has an immutable identifier
and records:

- capability ID and version;
- validated parameters;
- base-state precondition results;
- expanded primitive plan;
- patch and affected files;
- verification evidence;
- duration and economic measurements.

## Cheap capability selection

The external coding agent selects capabilities semantically, but it must not read every full manifest. SEH
exposes a compact catalogue projection containing only:

```text
id + version + intent.summary + use_when + do_not_use_when + parameter summary
```

Templates, examples, primitive steps, and applicability internals remain outside the model context. SEH first
filters the catalogue deterministically using repository applicability; the agent then chooses from the small
remaining projection and supplies parameters.

Selection therefore follows:

```text
installed catalogue
    → deterministic applicability filter
        → compact intent projection
            → semantic choice by the external agent
                → deterministic operation
```

## Phase 0 output and current status

Phase 0's technical gate is closed. Its retained sequence is intentionally asymmetric:

1. implement `seh capability validate` manually, creating the command group; this one-time setup is not a
   capture event;
2. from a recorded clean Git baseline, implement and accept `seh capability install` manually, then capture
   its structural patch;
3. derive `add-capability-subcommand` from the accepted `install` event and validate it with the already
   implemented `validate` machinery;
4. have the capability generate `seh capability run` as the developer-approved generalization event.

That sequence is now preserved as executable evidence under `experiments/phase0/real_capture/`: `install`
replays the accepted structural subset byte for byte; `run` was proposed before its implementation, approved
by the developer, and passes generalization; the retained candidate also passes idempotency and safe refusal.
This closes technical feasibility only. Token, latency, authoring-cost, and payback measurements remain open.

Using `validate` to judge a capability learned from `install` is not circular: the validator is the machine
that evaluates a candidate, while the candidate is project data describing a repeatable edit. See
[`PHASE0_FINDINGS.md`](PHASE0_FINDINGS.md).

The phase delivers:

1. a provisional closed primitive vocabulary supported by one retained real capability;
2. a capability package with prospectively captured pre-implementation fixtures and structural expected
   patches;
3. source-preserving AST-location plus textual splice in the product runtime;
4. all four gates passing for the retained capability.

The full record is [`PHASE0_FINDINGS.md`](PHASE0_FINDINGS.md).

The Phase 0 production CLI is intentionally restricted to `validate`, `install`, and `run`. A final schema,
MCP surface, arbitrary scripts, capability composition, and extension points remain outside this phase. Its
question is narrower:

> What is the smallest deterministic language that can express multiple real recurring change events of this
> project without losing source fidelity?
