# SEH Architecture

## Thesis

A coding agent should not spend model tokens rediscovering facts that the software environment can compute. SEH separates deterministic engineering operations from probabilistic reasoning and introduces explicit escalation boundaries.

Before AI agents, IDEs already automated much of this deterministically: IntelliSense, live templates,
"Generate →", refactorings that composed whole classes for a single purpose. Agents redo that same work
probabilistically — slower, costlier, and error-prone. SEH's core idea is to give that determinism back:
**have the external agent author a project-specific capability once, validate it deterministically, and
instantiate it forever with no inference in the execution path (~0 tokens, milliseconds).** It is the
IntelliJ live template, for agents, measured.

Cost is tracked on **two axes, not one**: tokens *and* latency. Replacing an inference round-trip (3–8s)
with an AST operation (ms) is measured at 8.7x latency improvement and up to 99% token savings on repeated
tasks — latency is often the more perceptible win day to day.

SEH is **self-contained**: it does not require an externally installed server to operate, and it ships as
an MCP server so it works unmodified across MCP-speaking coding agents (Claude Code, Codex, Kimi CLI, and
others). The differentiator is *not* repository indexing (solved by Serena and Aider) nor universal
refactoring (solved by act101, OHM-MCP, Code Scalpel) — those are consumed or kept deliberately minimal.
It is the **composite, project-specific capability**: one that both creates new files and inserts
structurally into existing ones, which template scaffolders (cookiecutter, plop, hygen) cannot do. Full
rationale in `.claude/PRPs/prds/seh-runtime-evidencia-medicao.prd.md`. The developer-facing learning loop is
illustrated in [`PRODUCT_SCENARIO.md`](PRODUCT_SCENARIO.md); the unit of learning and its deterministic
language are defined in [`CAPABILITY_MODEL.md`](CAPABILITY_MODEL.md).

## Core components

### seh-graph
Builds and stores a repository graph containing code artifacts and relationships.
The default implementation discovers the canonical Git root, parses tracked Python
sources with the stdlib `ast` module (zero external dependency), and atomically
stores a versioned graph in SQLite. Symbol resolution never guesses: ambiguous
name matches (e.g. two symbols reachable through different import paths) are
reported as `ambiguous`, never silently picked.

Every graph records the canonical repository root, Git HEAD (including unborn
repositories), tracked-worktree fingerprint, index timestamp, indexer version,
and schema version. Read operations reject stale or incompatible evidence.

This layer is deliberately minimal — enough for evidence to reference
`file:line:symbol` and for capabilities to anchor structural insertions,
not an attempt to match the indexing depth or language coverage of Serena or
Aider. The Java/Tree-sitter adapter built in PR #1 is frozen as an architectural
reference (it originated the provenance/fingerprint discipline described above)
but is out of the default indexing path.

### seh-capabilities *(the product)*
The project's versioned procedural memory: stores and instantiates composite, project-specific engineering
capabilities.

The model has three levels: a **primitive** is a project-agnostic deterministic instruction implemented by
SEH; a **capability** (`seh.capability/v0.1`) composes primitives, templates, applicability, parameters,
verification, and examples; an **operation** is one immutable invocation of a capability against a compatible
base state. Capabilities are versioned in `.seh-capabilities/`; operation records are local runtime evidence.

Lifecycle: **establish Git baseline** (the coding task starts in a clean worktree and records its tree) →
**implement** → **offer** (after the change succeeds, the agent notices a reusable procedure) → **confirm**
(the *developer* decides — after one occurrence recurrence can only be predicted, not known) → **materialize
capture** (copy the declared `before` bytes from the recorded baseline and the accepted structural patch from
the diff) → **propose** (the external agent authors a candidate: manifest, templates, and fixtures, paying
the generalization cost once) → **review candidate locally** (the developer inspects the manifest,
templates, fixtures, and every declared command) → **validate**
(`seh capability validate --allow-verification` runs the four gates below after an
explicit trust decision) → **install** (`seh capability install` promotes the candidate into
`.seh-capabilities/`, versioned and reviewable by the team in a PR) → **run** (`seh capability run`
instantiates a deterministic operation with no inference in the path) → **verify**
(`seh-runtime` executes the suite) → **measure** (`seh-evidence` records tokens and latency avoided).

`run` is plan-only unless the developer supplies both `--apply` and `--allow-verification`. An operation ID
content-addresses the capability version, normalized parameters, declared base bytes and modes, and patch.
Application refuses symlinks and stale base bytes, uses exclusive mode-preserving replacements, rolls back
ordinary partial promotion failures, and rejects a verifier that changes any declared result. Verification
commands remain explicitly trusted processes rather than an operating-system sandbox.

SEH does not author with an LLM. The agent writes the candidate; SEH only judges it. Local review before
validation protects the machine executing candidate-declared commands; PR review after installation protects
the shared catalogue. `validate` and `install` are separate because a rejected candidate must never reach it.

Generalization — separating structure from domain in a concrete implementation — belongs to the external
agent, which has just written the code and knows which parts carry meaning. SEH never infers that boundary.
Capabilities scaffold and wire structure; they do not author new domain behavior. A later behavioral edit by
the agent is separate from the deterministic operation and is measured separately, never smuggled into a
model-generated capability parameter.

#### The four gates

A candidate becomes a capability only if it clears all four:

1. **Fidelity** — instantiating it reproduces the accepted structural subset declared during capture.
   Behavioral edits outside the capability boundary are explicitly excluded from the expected patch.
2. **Generalization** — it produces a correct second case with different parameters. The agent proposes the
   second case; the developer approves or edits it, so a candidate is never graded solely against an example
   its own author chose. Fidelity alone proves memorization, not reuse.
3. **Idempotency** — re-applying it does not duplicate or corrupt what it already produced.
4. **Safe refusal** — an incompatible repository structure yields an explicit error, never a partial or
   adapted result.

#### Deterministic mechanics

Python AST nodes locate and validate source spans; they never rewrite source. Effects splice rendered text at
exact offsets and preserve all bytes outside their declared fragments. `ast.unparse()` is excluded because
even an unchanged parse/unparse round trip destroys comments and reformats code. Locators derive indentation,
separators, and trailing commas from siblings of the same structural parent; effects apply that style. Human
groupings absent from the grammar must be declared by the capability rather than guessed from whitespace.

The primitive algebra is closed in the MVP: projects compose only locators, splice effects, and verification
primitives admitted through real capabilities and versioned by SEH. `file.render` remains a candidate, not a
provisional primitive: no retained recurring event has exercised file creation yet. Arbitrary hooks,
project-defined primitives, model-generated code slots, and capability-to-capability composition are
excluded.

Fidelity and the other gates run against versioned, scoped fixtures materialized from a recorded clean Git
baseline. The baseline is cheap task-start evidence, not a continuous edit ledger. If the task did not start
from a clean worktree, or its baseline was not recorded, SEH cannot distinguish pre-existing edits from the
accepted change and must refuse capture. A fixture must never be reconstructed by subtracting the final
snapshot. Repository multiplicity also does not prove recurrence: capability candidates require repeated
change events, not merely similar structures. The first spike has not yet exercised fidelity or
generalization correctly; its evidence and open questions are recorded in
[`PHASE0_FINDINGS.md`](PHASE0_FINDINGS.md). Determinism is not "same parameters → same repository". It is:

```text
capability + parameters + compatible base state → same operation plan and patch
```

Comparison is scoped to the patch and to the files the capability declares it touches — an unrelated change
elsewhere in the repository must never invalidate it. The first retained real capture now exercises
fidelity and developer-approved generalization; its executable evidence is recorded under
`experiments/phase0/real_capture/`. Compatibility of the base state is checked
through local preconditions, not a global fingerprint:

- the expected symbol exists;
- the anchor is of the declared kind;
- the hash of the relevant structural fragment matches;
- the artifact to be created is absent;
- the capability's schema version is supported.

When a precondition fails the capability refuses to instantiate an operation and reports which one — it does
not adapt. The full mechanics, initial primitive vocabulary, fixture layout, selection projection, and MVP
composition boundaries are specified in [`CAPABILITY_MODEL.md`](CAPABILITY_MODEL.md).

### seh-ir
Represents engineering intent, scope, constraints, verification requirements, budgets and escalation policy in a model-neutral form.

### seh-context
Compiles an Engineering IR task plus repository evidence into a bounded context package.

### seh-runtime
Executes deterministic operations and verification — build, test, lint, diff, impact analysis and policy checks —
**outside the model's context window**. This is the primary economic lever: the agent never ingests raw
tool output directly.

### seh-evidence
Normalizes runtime outcomes into structured evidence for local recovery or frontier escalation, reusing the
provenance/fingerprint discipline from `seh-graph` (confident evidence or an explicit error, never stale
data served silently). Also owns token measurement: capturing input/output/cache consumption per agent
session so the economics of `seh-runtime` are provable, not asserted.

### seh-adapters
Integrates external coding agents and language implementations without coupling them to SEH internals.

The Python language adapter (stdlib `ast`) is the default. The Java adapter from PR #1 remains available but
frozen. Third-party context tools such as Serena may be wired in as an **optional benchmark reference**
(quantifying how much economy comes from semantic navigation alone) — never as a runtime dependency of SEH
itself.

This component adapts *agents and languages*, never model providers: there is no model adapter on any
roadmap, because SEH never calls a model (invariant 2). Engineering IR, context compilation, deterministic
runtime and evidence policy remain roadmap capabilities; see `docs/ROADMAP.md`.

## Architectural invariants

1. A consuming coding agent should not invoke a model for work that a deterministic SEH capability can
   answer with sufficient confidence.
2. **SEH never calls a model — ever.** Not during capability validation or operation execution. The external
   coding agent does all reasoning and authors the capability; SEH validates, stores, executes, and measures it. SEH
   therefore needs no API key, no provider, no billing and no model configuration, in any milestone.
3. **No inference in the operation path.** Capability authoring pays the reasoning cost once, through the
   agent; every instantiation after that is pure execution.
4. **Deterministic or explicitly failed — never plausible.** Given the same capability, parameters, and
   compatible base state, an operation produces the same plan and patch over declared files or fails loudly.
   A capability whose structural anchor has drifted must not guess.
5. **A candidate must clear all four gates — fidelity, generalization, idempotency, safe refusal.**
   Reproducing its declared structural subset proves fidelity, not reuse: a capability that merely memorized
   one case passes gate 1 and fails the product. A refused capability is better than one that emits
   almost-correct code deterministically.
6. **Capture is developer-confirmed.** Recurrence cannot be known from a single occurrence, so SEH never
   installs a capability on its own initiative — the agent may offer, the developer decides.
7. SEH must install and operate without requiring any externally installed server. Third-party tools may be
   consumed optionally, never as a hard dependency.
8. Every deterministic capability must be measurable in **both tokens and latency**. The result determines
   whether it serves the original economic use case or only a different one; measurement is mandatory even
   when the outcome is unfavorable.
9. **Model selection, routing and inference are outside the product boundary — not deferred, excluded.**
   Local model adapters, frontier planners and routing policies belong to the consuming agent, never to SEH.
   This follows from invariant 2: a component that never calls a model has no reason to choose one.
