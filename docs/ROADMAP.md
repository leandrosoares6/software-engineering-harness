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
> Both **tokens and latency** are primary metrics: replacing inference (3–8s) with AST execution (ms) is
> measured at 8.7x latency improvement and up to 99% token savings on repeated tasks.
>
> SEH is self-contained (no external server required) and ships as an MCP server so it works with any
> MCP-speaking coding agent. The Java/Tree-sitter adapter from PR #1 is frozen; indexing moved to Python
> via the stdlib `ast` module.

## M0 — Foundation
- [x] CLI skeleton
- [x] Git integration
- [x] SQLite graph store
- [x] Java symbol prototype *(frozen — superseded by the Python adapter in M1)*
- [x] graph inspection
- [x] AST-backed Java language adapter *(frozen, out of the default indexing path)*
- [x] graph schema versioning

## M1 — Python Context Compiler
- [ ] **M1a (pulled into MVP Fase 1 — see PRD)**: Python adapter via stdlib `ast` (zero external dependency;
      replaces Java/Tree-sitter as the default) + `seh inspect`/`seh neighbors` working on Python repos.
      This is the exploration-compression lever: it exists mainly to let the agent locate a symbol and its
      relations without grepping and reading whole files — a cost that shows up on *every* task, not just
      the error-retry loop, which is why it could not wait for the full M1.
- [ ] **M1b (after the MVP verdict)**: Engineering IR v0.1 schema, task validation, budgeted/prioritized
      context package generation, blast-radius analysis — the full Context Compiler.

Deliberately minimal: enough for evidence to reference `file:line:symbol` and for the agent to query
structure directly, not an attempt to match Serena/Aider in indexing depth or language coverage.

## M2 — Deterministic Runtime, Evidence & Measurement
- [ ] command runner (executes test/build/lint outside the model's context)
- [ ] `pytest` output → structured evidence compressor
- [ ] structured evidence model (reuses the provenance/fingerprint discipline built in PR #1)
- [ ] measurement harness — **tokens and wall-clock latency** per task
- [ ] baseline vs. SEH benchmark on a reproducible POC project

## M3 — `seh capability`: Procedural Memory *(the product)*
- [ ] **feasibility spike first**: hand-write two capabilities of different shapes for already-repeated
      patterns in this repo; derive the smallest shared primitive algebra and make all four gates pass for
      both. Everything below is conditional on this
- [ ] `seh.capability/v0.1` format — intent, typed parameters, applicability, preconditions, primitive steps,
      templates, fixtures, verification, provenance
- [ ] closed, versioned primitive vocabulary — no project-defined plugins, arbitrary lifecycle hooks, or
      model-generated code slots in the MVP
- [ ] source-preserving Python edits — AST locates and validates exact spans; textual splice writes; never
      mutate and `ast.unparse()` the module
- [ ] `seh capability validate ./candidate` — runs the four gates against an agent-authored candidate and
      scoped pre-implementation fixtures
- [ ] `seh capability install ./candidate` — promotes a validated candidate into the catalogue; a rejected
      candidate never reaches it
- [ ] **the four gates**: fidelity (rebuilds its own first example), generalization (produces a correct
      second case, proposed by the agent and approved by the developer), idempotency (re-applying does not
      duplicate or corrupt), safe refusal (incompatible structure errors out explicitly)
- [ ] developer-confirmed capture — the agent may offer, the developer decides
- [ ] `seh capability run CAPABILITY_ID` — instantiates an immutable operation with no inference in the path
- [ ] **AST-anchored insertion into existing files** (the hard part scaffolders skip; one well-defined
      anchor kind in the MVP, not a generic engine)
- [ ] operation contract scoped to the patch: `capability + parameters + compatible base state → same operation
      plan and patch`, compared only over declared files, with local preconditions — never a whole-repository
      fingerprint
- [ ] compact catalogue projection — the model sees only intent and parameter summaries after deterministic
      applicability filtering; steps, fixtures, and templates stay outside its context
- [ ] capabilities versioned in `.seh-capabilities/`; operation records remain local evidence in `.seh/`
- [ ] no capability-to-capability composition in the MVP; capabilities compose only SEH primitives
- [ ] dogfooding: author, validate, and install two candidates of different shapes, including
      `add-cli-command`, then instantiate them against new cases
- [ ] payback curve: how many instantiations before a capability pays for its authoring cost

M1a, M2 and M3 all belong to the MVP, but M3 is the differentiator. M1a and M2 exist largely to serve it:
M1a provides the AST substrate that structural insertion needs, M2 verifies every operation and reports the
numbers.

The falsification point is **technical before economic**. First: can correct, reusable capabilities be
generalized from a single accepted implementation? That is answerable in days, by hand, with no benchmark —
and if the answer is no, nothing else matters, because a capability that emits almost-correct code
deterministically is worse than no capability at all. Only then does payback become the question.

## M4 — Distribution
- [ ] MCP server exposure (single-command install, no external process to configure) — exposes
      `capability run`, `inspect`, `neighbors`, `test`
- [ ] works unmodified across Claude Code, Codex, and Kimi CLI
- [ ] optional benchmark arm against Serena / OHM-MCP — market reference only, never a runtime dependency

## M5 — Future evolution
- [ ] derive candidate capabilities from past commits (offer capture without an explicit session)
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
