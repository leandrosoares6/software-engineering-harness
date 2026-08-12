# Software Engineering Harness (SEH)

> **Spend intelligence where it matters.**

SEH is a model-agnostic engineering harness designed to reduce unnecessary LLM usage during software development. It moves repository navigation, verification, orchestration, and repeatable engineering operations into deterministic code, leaving models to handle work that genuinely requires reasoning.

## Status

`0.1.0a3` — Python-first foundation prototype.

The first milestone intentionally contains **no LLM integration**. It proves the deterministic substrate first: Git-aware repository indexing, a structural graph, and queryable engineering context.

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
`expected.patch`, and a `scope.yaml` listing what it treated as structure and what it excluded as behaviour.

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
  PASS fidelity: patch and verification match
  PASS generalization: patch and verification match
  PASS idempotency: second application refused explicitly
  PASS safe_refusal: no module-level function starting with 'handler_'
```

Four gates, all required. **Fidelity** rebuilds the change you already accepted. **Generalization** produces a
second case with different parameters, which you approve — fidelity alone only proves memorization.
**Idempotency** refuses a second application. **Safe refusal** errors out on an incompatible tree instead of
adapting to it.

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

SEH is the project's versioned procedural memory. A coding agent handles a new pattern once; when that
pattern proves reusable, it can be crystallized as a deterministic capability. Instantiating that capability
produces an operation the project can execute, verify, and measure without inference. The developer continues
to work through natural-language prompts, while recurring engineering procedures progressively move out of
the model's context and into reviewable project capabilities.

See [Product Scenario: A Python Project That Learns How It Is Built](docs/PRODUCT_SCENARIO.md) for the
end-to-end developer experience and [SEH Capability Model](docs/CAPABILITY_MODEL.md) for the primitive,
capability, and operation mechanics. The economic experiment is specified separately in the
[M2 Measurement Protocol](docs/M2_MEASUREMENT_PROTOCOL.md).

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
