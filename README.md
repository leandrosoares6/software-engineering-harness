# Software Engineering Harness (SEH)

> **Spend intelligence where it matters.**

SEH is a model-agnostic engineering harness designed to reduce unnecessary LLM usage during software development. It moves repository navigation, verification, orchestration, and repeatable engineering operations into deterministic code, leaving models to handle work that genuinely requires reasoning.

## Status

> ## Closed as a product, 2026-08-17
>
> Three theses were tested to completion, each with its kill criterion fixed in writing before the
> run. All three closed. **[`docs/ENCERRAMENTO.md`](docs/ENCERRAMENTO.md) is the closing record** —
> read it before anything else here.
>
> - **Edit reuse** — dead on economics. The recurring procedure a field scan found recurred 3 times
>   in 5 months, with 4 mechanical lines out of 1242 insertions.
> - **Context compilation** — the value is real and measured (**52 → 16 tool calls**), but the
>   mechanism that would produce the package automatically was refuted: **0.10 / 0.00 / 0.00**
>   against a threshold of 0.30 fixed beforehand.
> - **Exposing mechanical operations** — the hypothesis is right and the position is taken. Serena
>   and others already ship LSP rename/move/extract over MCP, with token-saving figures published.
>
> The code works and the suite passes; nothing here was abandoned because it was broken. The two
> measurement scripts under `experiments/` depend on nothing in SEH and remain useful on any
> repository with a `git log`.

`0.1.0a3` — Python-first foundation prototype.

The first milestone intentionally contains **no LLM integration**. It proves the deterministic substrate first: Git-aware repository indexing, a structural graph, and queryable engineering context.

> **New to the project, or returning to it?** [`docs/COMO_FUNCIONA.md`](docs/COMO_FUNCIONA.md)
> (Portuguese) tells the whole thing as a usage scenario with no project vocabulary at all, and
> decodes the terms the rest of `docs/` uses.

## Try it in your project

Requires Python 3.11+ and a Git repository with tracked Python sources.

```bash
pip install git+https://github.com/leandrosoares6/software-engineering-harness.git
```

### 1. Index the repository

```bash
cd /path/to/your-project
seh init
seh index
```

`init` creates local state under `.seh/` and makes Git ignore it from the inside, so it never dirties your
working tree and never edits a file you own. `index` parses Git-tracked Python with the standard-library
`ast` module — no external parser, no language server.

### 2. Ask where things are

```bash
seh inspect build_registry
seh neighbors build_registry
```

```text
function:be3617ef88619f5b8de0  function  app.registry.build_registry  app/registry.py:8
```

`inspect` lists every partial match with a stable node ID. `neighbors` answers only when the query is
unambiguous; otherwise it prints the candidates so you can select one with `--id`. Neither command writes
anything, and both refuse a stale index rather than serving outdated results.

### 3. Teach the project a recurring procedure

This is what makes SEH more than an indexer. The loop starts with **ordinary work**: implement the change
yourself, or with your agent, exactly as you normally would. Only once it is accepted do you decide whether
the *surrounding procedure* is worth keeping.

Say adding a handler to `app/registry.py` always means the same two edits — a `handler_<name>` function, and
one line registering it. Implement one, commit it, then capture the procedure:

```bash
seh capability capture \
  --id app.add-registry-handler \
  --baseline <commit-before-your-change> \
  --file app/registry.py \
  --output ./candidate
```

`capture` reads the `before` bytes from the baseline commit — never by subtracting from the current tree,
because ordering and surrounding bytes are historical facts. It writes the fixtures, `accepted.patch`,
`expected.patch`, and a `scope.yaml` listing what it treated as structure, what it excluded as behaviour, the
two commits involved, and a digest of each patch.

Those last two matter. If a capability cannot express part of the change you accepted, declare that part
under `excluded` — do not adjust the patches to match what your templates happen to produce. Validation
recomputes the structural claim from the two commits and refuses a package that misrepresents them.

It deliberately stops there. `templates/`, `parameters` and `steps` are left as `TODO(agent)`, because
separating structure from domain is a judgement call and SEH must not make it for you. Fill them in — this is
where a coding agent earns its keep, having just written the code and knowing which parts carry meaning:

```jinja
{# candidate/templates/handler.py.tmpl #}
def handler_{{ name }}() -> str:
    return "{{ name }}"
```

```yaml
# candidate/capability.yaml (excerpt)
steps:
  - uses: splice.after
    with:
      file: app/registry.py
      locator: python.symbol
      selector: last_with_prefix
      prefix: handler_
      template: templates/handler.py.tmpl
```

### 4. Review it, then prove it

A candidate declares commands that SEH will execute on your machine, so read it
before granting that permission:

```bash
seh capability show ./candidate
```

`show` prints the parameters, preconditions, steps, every template body, and —
prominently — every command that would run, with its timeout. It executes
nothing.

```text
Verification commands — these WILL execute with your privileges
  $ python -m compileall -q app/registry.py
    timeout 30s, expects exit 0
  (no shell, argument vector only — this is not an OS sandbox)
```

Once you have read it:

```bash
seh capability validate ./candidate --allow-verification
```

```text
Capability app.add-registry-handler
  verified: expected.patch is consistent with 717e87797ec2..abbb477cfb40 (1 file/s)
  PASS fidelity: patch and verification match
  PASS generalization: patch and verification match
  PASS idempotency: second application refused explicitly
  PASS safe_refusal: no module-level function starting with 'handler_'
```

Four gates, all required. **Fidelity** rebuilds the change you already accepted. **Generalization** produces a
second case with different parameters, which you approve — fidelity alone only proves memorization.
**Idempotency** refuses a second application. **Safe refusal** errors out on an incompatible tree instead of
adapting to it.

The first line is **provenance**, and it is not a gate — it is what the gates are measured against. Every line
the capability claims to have produced is looked up in the accepted commit. `verified` means history agrees;
`unreachable` means the commits are no longer in the repository (a rebase, a squash merge, a fresh shallow
clone), so the patches rest on their recorded digests alone. It is printed either way, because those two are
not the same assurance. A package that contradicts its own commits is refused before any gate runs.

Verification is denied by default. A candidate declares commands that SEH will execute, so review it — every
command — before opting in with `--allow-verification`. Commands run with an argument vector, no shell, and a
bounded timeout, but that is not an operating-system sandbox.

### 5. Install and reuse

```bash
seh capability install ./candidate --allow-verification
```

The capability lands in `.seh-capabilities/`, which **is** version-controlled: learned procedure is explicit
code and data, reviewable in a pull request and removable in one.

From then on the procedure costs no inference. Check what the project has
learned, then instantiate it:

```bash
seh capability list
```

```text
app.add-registry-handler    v1  name
```

```bash
seh capability run app.add-registry-handler --param name=status
```

```text
Planned app.add-registry-handler v1 (1 file(s), nothing written)
Operation de23077335fd1bb1...
--- a/app/registry.py
+++ b/app/registry.py
@@ -5,7 +5,12 @@
+def handler_status() -> str:
+    return "status"
...
Rerun with --apply --allow-verification to write and verify this patch.
```

`run` plans by default and writes nothing. Review the patch, then apply it:

```bash
seh capability run app.add-registry-handler --param name=status --apply --allow-verification
```

```text
Applied app.add-registry-handler v1 to 1 file(s), verified, in 62ms
```

Inserted code adopts the surrounding style — indentation, separators and blank-line rhythm are read from the
siblings already in the file — so the result is indistinguishable from hand-written code, and every byte
outside the inserted fragment stays identical.

### What SEH will not do

It will not invent behaviour: a capability scaffolds and wires recurring structure, but the body of your new
handler is still yours to write. It will not adapt to a repository it does not recognize — a drifted anchor
is an explicit error, never a best guess. And it never calls a model: your agent does the reasoning, while
SEH judges, executes and measures.

## Principles

1. **Code before tokens.** If a task can be solved deterministically, do not ask an LLM.
2. **Local before frontier.** Prefer local intelligence for bounded implementation work.
3. **Frontier only for uncertainty.** Architecture, decomposition, ambiguity and replanning justify expensive reasoning.
4. **Evidence over conversation.** Runtime outcomes are structured evidence, not unbounded chat history.
5. **Context is compiled.** Agents receive the smallest useful context package, not the repository by default.
6. **Model agnostic.** SEH should wrap coding agents rather than become one.

## Product vision

**The active front is the Context Compiler** — see the
[Context Compiler PRD](docs/CONTEXT_COMPILER_PRD.md). The unit of value is no longer the reusable edit; it is
the repository's own knowledge, delivered in the right shape with verifiable origin.

Its first gate is closed and positive. A pre-registered six-session experiment took an agent from a
median of **52 tool calls to 16** on a real cross-layer localization task, against a threshold of
≤50% fixed before the first run — and all six sessions converged on the same solution, so what the
package bought was the *path* to the answer rather than the answer. Three limits are declared in
[the result](experiments/fase0/RESULT.md) and travel with the number: the package was hand-built by
the person who formed the hypothesis, so **this is the ceiling, not the product**; the oracle is
localization, not correctness; and it is one task in one repository.

Two questions remain open, and either can still end it: whether a repository's changes recur in the
same *region* often enough for accumulated path records to pay (Phase 0.5), and whether a
deterministic resolver recovers any of the ceiling (Phase 1, §16 of the PRD).

Phase 0.5 ran its instrument check first and **failed it** — in a mature repository the fraction of
a commit's files that *some* earlier commit already touched has a median of **1.00**, so "has this
region been visited before?" is a question whose answer is almost always yes
([record](experiments/region_recurrence/OSS_RESULT.md)). That collapsed the two open questions into
one: retrieval.

**Retrieval was then measured, and it failed.** Ranking prior commits by weighted term overlap
against the request text recovers **0.10 / 0.00 / 0.00** of the available opportunity on the three
repositories, against a threshold of 0.30 fixed before the script existed, and beats "just look at
the last five commits" by 9.5 points where 15 were required. Where a request term already appears
in the target's own file paths, all three score an identical 0.25 — the signature of `grep`. The
case the product exists for is the other one. Record and full method in
[seed_retrieval/RESULT.md](experiments/seed_retrieval/RESULT.md).

So the position is: **a correct context package is worth roughly 3× in exploration, and there is no
cheap deterministic way to produce one.** The one thing that could still overturn it is the field
repository, whose commit subjects are written in the developer's domain language — the property the
three open-source repositories are weakest in. That prediction is registered, and the test is one
command.

### The capability machinery is superseded

It is retained as evidence and is not being extended. It works and is covered by tests; what stopped it was a
measurement. A field scan of a production repository found a genuine recurring procedure of exactly the shape
capabilities target — and it recurred **three times in five months**, its mechanical share was **four lines out
of 1242 insertions**, and the three primitives it would have needed do not exist. Break-even lands in years.

That negative result is the strongest thing this project produced, and it is what justifies the pivot. The
record is in [Phase 0 Findings](docs/PHASE0_FINDINGS.md) and §2 of the PRD — which is also explicit that the
replacement hypothesis, *discovery is expensive*, is **not yet established**, and that a one-day experiment
with a kill criterion comes before any code.

One piece carried over intact: **provenance anchoring**. A context package reuses the same mechanism, so it
knows which commit it describes and fails loudly instead of going stale.

Read [Product Scenario](docs/PRODUCT_SCENARIO.md) and the [SEH Capability Model](docs/CAPABILITY_MODEL.md) as
the record of that earlier design, and the [M2 Measurement Protocol](docs/M2_MEASUREMENT_PROTOCOL.md) as the
experiment it never completed.

## Current CLI

```bash
seh init
seh index
seh inspect UserService
seh neighbors UserService
seh neighbors --id class:0123456789abcdef0123
seh capability validate ./candidate --allow-verification
seh capability install ./candidate --allow-verification
seh capability list
seh capability show ./candidate
seh capability capture --id app.x --baseline HEAD~1 --file app/registry.py --output ./candidate
seh capability run seh.add-capability-subcommand --param name=report
seh capability run seh.add-capability-subcommand --param name=report --apply --allow-verification
```

`inspect` lists every partial match with its stable node ID and qualified name.
`neighbors` succeeds only for an unambiguous query; when several nodes match, it
lists candidates that can be selected with `--id`. Read commands reject missing,
legacy, or stale indexes and never create repository state.

`capability validate` is the hand-built Phase 0 vertical slice. It loads a restricted
`seh.capability.phase0/v0.1` candidate, executes fidelity, developer-approved generalization,
idempotency, and safe-refusal gates in memory, and runs declared verification commands in a temporary
working copy. It validates candidates but never installs or runs them against the working tree. Verification
is denied by default: review the candidate locally, especially every command, then opt in with
`--allow-verification`. Commands use an argument vector with no shell and a bounded timeout, but they are not
an operating-system sandbox.

`capability install` stages a byte-exact snapshot under ignored local `.seh/` state, revalidates it, and
promotes it atomically to
`.seh-capabilities/<capability-id>` under the canonical Git root. It applies the same explicit verification
trust boundary as `validate`, refuses symlinks and special files, and never overwrites an installed
capability. A failed gate or promotion leaves no partial capability in the catalogue.

`capability run` plans by default: it loads an installed capability, validates typed parameters and local
preconditions, and prints a deterministic patch plus a content-addressed operation ID without writing.
Applying requires both `--apply` and explicit `--allow-verification`. Writes use exclusive sibling
temporaries, preserve file modes, refuse symlinks and stale base bytes, and restore declared files if
promotion or verification fails. A verifier that changes any declared result is rejected and rolled back.

## Architecture direction

```text
Developer prompt
    │
    ▼
External coding agent
    │
    ├── novel work ──► reason and implement ──► propose capability
    │
    └── learned work ──► select installed capability
                              │
                              ▼
                    deterministic primitive plan
                              │
                              ▼
                         operation patch
                              │
                              ▼
                    verification and evidence
```

## v0.1 scope

- Git repository discovery
- zero-infrastructure SQLite graph store
- Python indexing with the standard-library `ast` module
- symbol inspection
- neighborhood queries
- schema-versioned graph provenance and freshness checks
- no LLM dependency

The Python adapter indexes modules, classes, nested classes, functions, methods,
signatures, imports, and inheritance. Only Git-tracked files are indexed;
unsupported, external, or ambiguous references are reported without creating
speculative graph edges.

## License

Apache-2.0.
