# Roadmap

> Positioning decided in `.claude/PRPs/prds/seh-runtime-evidencia-medicao.prd.md`.
>
> **SEH is the project's versioned procedural memory** — a codebase that learns how it is built. The agent
> handles novel work; once a recurring procedure proves reusable and the *developer confirms it*, it is
> crystallized into a deterministic capability. Each invocation instantiates an operation the project
> executes, verifies and measures without inference.
> Learning is explicit code and data: versioned, inspectable, testable, removable in a PR — no hidden model
> training. See [`PRODUCT_SCENARIO.md`](PRODUCT_SCENARIO.md).
>
> The unit of learning — primitive, capability, operation — plus the closed primitive algebra, the
> source-preserving edit contract, and the four gates are defined canonically in
> [`CAPABILITY_MODEL.md`](CAPABILITY_MODEL.md). This roadmap sequences that model; it does not redefine it.
>
> Symbol indexing and evidence compression are supporting levers, not the differentiator — that layer is
> occupied by Serena, Aider, act101 and OHM-MCP. Cost savings are a consequence of the thesis, not the pitch.
>
> Both **tokens and latency** are primary metrics. External deterministic-replay research reports 8.7x
> latency improvement and up to 99% token savings on repeated tasks; these figures are motivation, not SEH
> results. SEH's own economic hypothesis remains open until M2 runs the three-arm experiment.
>
> SEH is currently a self-contained CLI with no external server requirement. MCP distribution is the M4
> target. Python via the stdlib `ast` module is the only graph-indexing path.

## M0 — Foundation
- [x] CLI skeleton
- [x] Git integration
- [x] SQLite graph store
- [x] Python symbol indexing via the standard-library AST
- [x] graph inspection
- [x] graph schema versioning

## M1 — Python Context Compiler
- [x] **M1a (pulled into MVP Fase 1 — see PRD)**: Python adapter via stdlib `ast` (zero parser dependency)
      + `seh inspect`/`seh neighbors` working on Python repos.
      This is the exploration-compression lever: it exists mainly to let the agent locate a symbol and its
      relations without grepping and reading whole files — a cost that shows up on *every* task, not just
      the error-retry loop, which is why it could not wait for the full M1.
- [ ] **M1b (after the MVP verdict)**: Engineering IR v0.1 schema, task validation, budgeted/prioritized
      context package generation, blast-radius analysis — the full Context Compiler.

Deliberately minimal: enough for evidence to reference `file:line:symbol` and for the agent to query
structure directly, not an attempt to match Serena/Aider in indexing depth or language coverage.

## M2 — Deterministic Runtime, Evidence & Measurement

Implementation and experiment contract: [`M2_MEASUREMENT_PROTOCOL.md`](M2_MEASUREMENT_PROTOCOL.md).

- [ ] command runner (executes test/build/lint outside the model's context)
- [ ] `pytest` output → structured evidence compressor
- [ ] structured evidence model (reuses the provenance/fingerprint discipline built in PR #1)
- [ ] measurement harness — **tokens and wall-clock latency** per task
- [ ] three-arm A/A′/B benchmark on a reproducible POC project: baseline agent, documented procedure, SEH

## M3 — `seh capability`: Procedural Memory *(the product)*
- [x] **initial source-preservation spike**: proved AST→offset plus textual splice, executable scaffolding,
      idempotency, and safe refusal. It explored a wider vocabulary against the Java adapter, which was
      removed in the Python-only migration; the surviving lessons are recorded in
      [`PHASE0_FINDINGS.md`](PHASE0_FINDINGS.md), the primitives it exercised are not admitted
- [x] **Phase 0 gate closed with required product events**: `validate` was implemented by hand as one-time
      group setup and excluded from fidelity data; `install` was captured from a clean Git baseline;
      `add-capability-subcommand` was derived from it; and developer-approved `run` closed generalization
- [ ] `seh.capability/v0.1` format — intent, typed parameters, applicability, preconditions, primitive steps,
      templates, fixtures, verification, provenance
- [x] closed, versioned Phase 0 primitive vocabulary — only primitives exercised by real retained events;
      `file.render` remains excluded until a recurring procedure genuinely creates files
- [x] source-preserving Python edits — AST locates and validates exact spans; textual splice writes; never
      mutate and `ast.unparse()` the module
- [x] `seh capability validate ./candidate` — restricted Phase 0 profile runs the four gates against an
      agent-authored candidate and scoped pre-implementation fixtures; the final public schema remains open
- [x] `seh capability install ./candidate` — promotes a validated candidate into the catalogue; a rejected
      candidate never reaches it
- [x] **the four gates**: fidelity (rebuilds its own first example), generalization (produces a correct
      second case, proposed by the agent and approved by the developer), idempotency (re-applying does not
      duplicate or corrupt), safe refusal (incompatible structure errors out explicitly)
- [ ] developer-confirmed capture — every eligible task records a clean Git baseline; after success the
      agent may offer and the developer decides; missing or dirty baseline causes explicit refusal
- [x] `seh capability run CAPABILITY_ID` — plans by default and instantiates a content-addressed immutable
      operation with no inference in the path; apply requires explicit verification consent
- [x] **AST-anchored insertion into existing files** (the hard part scaffolders skip; one well-defined
      anchor kind in the MVP, not a generic engine)
- [x] operation contract scoped to the patch: `capability + parameters + compatible base state → same operation
      plan and patch`, compared only over declared files, with local preconditions — never a whole-repository
      fingerprint
- [ ] compact catalogue projection — the model sees only intent and parameter summaries after deterministic
      applicability filtering; steps, fixtures, and templates stay outside its context
- [x] installed Phase 0 capability packages live in version-controlled `.seh-capabilities/`
- [ ] persist immutable operation records as local evidence in `.seh/`
- [x] Phase 0 excludes capability-to-capability composition; capabilities compose only supported SEH
      primitives
- [ ] dogfooding: validate and install `add-capability-subcommand` plus one candidate of a genuinely different
      shape, then instantiate both against new real cases
- [ ] payback curve: how many instantiations before a capability pays for its authoring cost

M1a, M2 and M3 all belong to the MVP, but M3 is the differentiator. M1a and M2 exist largely to serve it:
M1a provides the AST substrate that structural insertion needs, M2 verifies every operation and reports the
numbers.

The falsification point is **technical before economic**. The first retrospective spike correctly failed;
the prospectively captured `install` → `run` sequence subsequently passed fidelity and developer-approved
generalization without expanding the primitive vocabulary for coverage. Technical feasibility is closed.
Payback — tokens, latency, authoring cost, and repetitions to amortize a capability — is now the open test.

## M4 — Distribution
- [ ] MCP server exposure (single-command install, no external process to configure) — exposes
      `capability run`, `inspect`, `neighbors`, `test`
- [ ] works unmodified across Claude Code, Codex, and Kimi CLI
- [ ] optional benchmark arm against Serena / OHM-MCP — market reference only, never a runtime dependency

## M5 — Future evolution
- [ ] derive candidate capabilities from past commits only when a real parent tree preserves the exact
      `before` state; squash/rebase gaps cause refusal, never reconstruction by subtraction
- [ ] capability catalogue retrieval — as the vocabulary grows, selecting the wrong capability produces the
      wrong result quickly and confidently; applicability declarations and loud preconditions are the
      current containment, not a solution
- [ ] capability health in CI — installed capabilities re-validated on every build, so drift surfaces as a
      failing check rather than as bad generated code

## Outside the product boundary

Local model adapters, frontier planners and model routing policies are **not deferred features — they are
excluded by design**. SEH never calls a model (architectural invariant 2), so it has no reason to choose
one. That responsibility belongs to the consuming coding agent. SEH owns the deterministic, measurable half
of the loop; the probabilistic half stays where it already lives.
