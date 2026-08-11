# Product Scenario: A Python Project That Learns How It Is Built

## The idea

SEH acts as the project's versioned procedural memory.

A coding agent still interprets the developer's natural-language request and reasons about work that is
new, ambiguous, or domain-specific. What changes over time is that the agent no longer needs to rediscover
how the project performs recurring engineering work. Once a successful pattern is captured as a versioned
capability, SEH can instantiate it deterministically, verify the resulting operation, and return compact
evidence.

The resulting learning loop resembles a junior developer becoming familiar with a codebase:

1. The first occurrence requires exploration, reasoning, implementation, and feedback.
2. Once it succeeds, the agent may observe that the surrounding procedure looks reusable and offer to
   capture it.
3. The developer confirms — they are the one who knows whether the pattern actually recurs in this project —
   and it is crystallized as a reviewable, project-specific capability.
4. Future requests reuse that learned procedure without inference in the operation path.

Capture is deliberately developer-confirmed rather than automatic. After a single occurrence nothing can
*know* that a pattern recurs; it can only predict it. Asking keeps the catalogue small and trustworthy, and
places the judgement with the person who has the project context to make it.

This is continuous learning without hidden model training. The learned knowledge is explicit code and data:
versioned, inspectable, testable, and removable in a pull request.

The precise distinction between primitive, capability, and operation is defined in
[`CAPABILITY_MODEL.md`](CAPABILITY_MODEL.md).

## Example project

Consider a Python chat-agent application with a structure such as:

```text
python-chat-agent/
├── app/
│   ├── api/
│   │   └── routes/
│   ├── agents/
│   │   ├── chat_agent.py
│   │   └── registry.py
│   ├── tools/
│   │   ├── get_customer.py
│   │   └── search_knowledge.py
│   ├── schemas/
│   └── services/
├── tests/
│   ├── agents/
│   └── tools/
├── pyproject.toml
├── .seh/                  # local state: graph db, cache, evidence (gitignored)
└── .seh-capabilities/     # the procedural memory: versioned, reviewed in PRs
```

The developer interacts with their coding agent normally. They do not need to know the capability format,
AST anchor types, or SEH commands.

## First occurrence: the project has not learned the pattern yet

The developer asks:

> Add a tool to the chat agent that returns a customer's upcoming appointments. It must receive the
> customer ID, call the scheduling service, be registered with the agent, and include tests.

No compatible capability exists yet. The agent therefore follows the cold path:

```text
Developer prompt
    │
    ▼
Agent verifies a clean Git worktree and records the baseline tree
    │
    ▼
Agent interprets the requirement
    │
    ├──► SEH locates relevant Python symbols and relationships
    │
    ▼
Agent reasons about and implements the new behavior
    │
    ├──► SEH runs focused tests, linting, and type checks
    │        │
    │        └──► compact, structured evidence
    │
    ▼
Successful implementation
    │
    ├──► agent offers to capture the surrounding procedure
    │         │
    │         └── developer declines ──► finish
    │
    └── developer confirms
         │
         ▼
Agent authors a capability candidate: manifest, templates, fixtures, and a proposed second case
         │
         ▼
Developer approves or edits the second case
         │
         ▼
seh capability validate ./candidate
         │
         ├── fidelity ── generalization ── idempotency ── safe refusal
         │
         ├── any gate fails ──► rejected, with the divergence reported
         │
         └── all gates pass ──► seh capability install ──► .seh-capabilities/
```

Every coding task that may produce project memory starts from a clean Git worktree and records its baseline
tree. This is constant-size provenance, not a resident edit ledger. After the implementation succeeds and the
developer confirms capture, the agent materializes the declared `before` bytes from that baseline and the
accepted structural patch from the diff. If no clean baseline was recorded, capture refuses: it never
manufactures a `before` state by deleting resulting lines later. Similar structures in the final repository
do not prove recurrence; the capability is justified by repeated change events or by a prospective second
event approved by the developer.

During this first implementation, the agent discovers that adding a tool to this project consistently
requires it to:

1. Create a module under `app/tools/`.
2. Define the tool input schema and callable.
3. Import the tool into `app/agents/registry.py`.
4. Add it to the collection exposed to the chat agent.
5. Create a unit test for the tool.
6. Update the integration test for the agent registry.
7. Run the project's focused quality checks.

The domain behavior remains specific to the request. The surrounding engineering procedure is the reusable
part.

This final-state scenario eventually needs a file-creation primitive. Phase 0 does not admit `file.render`
preemptively: it enters the closed vocabulary only after real retained change events demonstrate that file
creation is part of a recurring procedure and the primitive clears the same gates.

## Crystallization: turning experience into project capability

After the implementation passes, the agent offers to capture a capability named `add-agent-tool`. Once the
developer confirms, the agent pays the reasoning cost once to author a candidate that expresses the
discovered procedure as parameters, preconditions, effects, and verification steps.

The hard part of this step is **generalization**: the first implementation produced a concrete file, and
turning it into a reusable template means separating what is structural from what is domain-specific. The
external agent is the right participant to do this — it has just written the code and knows which parts
carry meaning. SEH does not attempt to infer that boundary from the diff.

SEH's job is to keep the agent honest about it. The candidate is submitted to `seh capability validate`,
which runs four gates, and only a candidate that clears all four reaches the catalogue through
`seh capability install`:

| Gate | Question | Why it is not redundant |
| --- | --- | --- |
| Fidelity | Does it rebuild the accepted structural subset declared at capture? | Establishes that the capability is faithful without pretending to author domain behavior |
| Generalization | Does it produce a correct second case with different parameters? | Fidelity alone proves memorization. This is the gate that proves *reuse* |
| Idempotency | Does re-applying it avoid duplicating or corrupting? | Registries and subparsers are append targets; a second run must not double-register |
| Safe refusal | Does an incompatible structure fail loudly? | A capability that adapts silently is worse than one that stops |

The second case is proposed by the agent and approved — or edited — by the developer, so a candidate is
never graded solely against an example its own author selected.

Because the accepted implementation already exists when the candidate is authored, each gate runs against a
small versioned fixture materialized from the clean Git baseline recorded before that implementation. The
fixture contains only declared files and survives later Git rebases or squash merges. A task that began from
an unrecorded or dirty baseline is ineligible for capture.

Better a refused capability than one that emits almost-correct code deterministically.

A capability may cover only the structural envelope of the developer's request. It can create a handler
skeleton, register it, and make it fail loudly while the external agent writes genuinely new domain behavior
as a separate edit. That edit is not a code slot in the capability and is measured outside the deterministic
operation.

Conceptually, the capability may accept:

```yaml
name: get_upcoming_appointments
description: Return a customer's upcoming appointments
input:
  customer_id: str
service:
  module: app.services.scheduling
  function: get_upcoming_appointments
```

Its declared effects can then:

- create the tool module and its unit test from project-owned templates;
- locate the registry using Python syntax rather than line numbers;
- insert the import and registry entry without rewriting unrelated code;
- update the agent integration test;
- run syntax, lint, type, and test verification;
- fail explicitly if the expected project structure has drifted.

Python AST is used only to locate and validate structural anchors. SEH derives the exact source offset and
splices locally styled text into the existing file; it never rewrites the tree through `ast.unparse()`. This
preserves comments, formatting, and every byte outside the declared fragment.

Instantiation is deterministic relative to a compatible base state: the same capability and parameters
produce the same operation plan and patch over declared files. Local preconditions validate expected symbols
and anchors; unrelated repository changes do not invalidate the capability.

Candidate authoring is LLM-assisted, but SEH itself never calls a model. The external coding agent writes
the candidate; SEH validates, installs, executes, and measures it.

## Later occurrence: the project already knows the procedure

Weeks later, a developer asks:

> Create a tool that returns a customer's open invoices and make it available to the chat agent.

The coding agent interprets the request and finds the compatible `add-agent-tool` capability exposed by SEH.
It maps the natural-language intent to capability parameters:

```yaml
name: get_open_invoices
description: Return a customer's open invoices
service:
  module: app.services.billing
  function: get_open_invoices
```

SEH takes the warm path and instantiates an operation:

```text
Developer prompt
    │
    ▼
Agent interprets intent and selects add-agent-tool from a compact catalogue projection
    │
    ▼
SEH validates local preconditions
    │
    ├── creates app/tools/get_open_invoices.py
    ├── updates app/agents/registry.py through structural anchors
    ├── creates and updates the relevant tests
    └── runs the declared verification
    │
    ▼
Compact evidence returned to the agent
    │
    ▼
Agent reports the outcome to the developer
```

The evidence can be as small as:

```yaml
capability: add-agent-tool
operation_id: op_01...
status: success
changes:
  created:
    - app/tools/get_open_invoices.py
    - tests/tools/test_get_open_invoices.py
  modified:
    - app/agents/registry.py
    - tests/agents/test_registry.py
verification:
  ruff: passed
  type_check: passed
  pytest:
    passed: 14
    failed: 0
duration_ms: 1380
inference_during_operation: false
```

The agent can now answer the developer directly:

> The `get_open_invoices` tool was created and registered with the chat agent. Unit and integration tests
> were added, and linting, type checking, and all 14 focused tests passed.

The model interpreted the intent and communicated the result. It did not need to rediscover the project
layout, reread similar tools, reconstruct the registry convention, generate recurring boilerplate, or
inspect raw test output.

Selecting the right capability is the agent's responsibility, and it becomes harder as the catalogue grows —
a wrong selection now produces the wrong thing quickly and confidently. SEH first filters capabilities by
applicability and exposes only compact intent metadata, never templates or primitive steps, to the model.
Each capability declares when it applies and preconditions fail loudly rather than adapting. A capability is
trusted executable knowledge, not a suggestion, so it must refuse a repository it does not recognize.

## Division of responsibility

| Participant | Responsibility |
| --- | --- |
| Developer | Express intent, constraints, and acceptance criteria |
| Coding agent | Interpret intent, make decisions, and handle novel work |
| `seh-capabilities` | Store and instantiate known project-specific procedures |
| `seh-graph` | Locate symbols and validate structural anchors |
| `seh-runtime` | Run builds, tests, linting, type checks, and policies |
| `seh-evidence` | Preserve provenance and compress execution outcomes |
| Developer | Review meaningful changes and decisions rather than mechanical work |

The boundary is deliberate:

```text
"How should the agent's memory be redesigned?"       → coding agent
"How does this project add another agent tool?"      → SEH capability
"Did the change pass tests and evaluations?"         → SEH runtime and evidence
"Does the failure require an architectural choice?"  → coding agent
```

SEH does not automate the business decision. It automates the engineering procedure that surrounds a
decision once that procedure is known.

## Other procedures the project can learn

The same Python project may gradually accumulate a small, focused procedural vocabulary:

| Developer request | Learned capability |
| --- | --- |
| Add another tool to the agent | `add-agent-tool` |
| Create an authenticated API endpoint | `add-api-route` |
| Add a source to the retrieval pipeline | `add-knowledge-source` |
| Add an agent evaluation case | `add-agent-eval-case` |
| Add an application setting | `add-application-setting` |
| Create an event consumer | `add-event-handler` |
| Add a chat message type | `add-message-type` |

These are not universal Python refactorings. Each capability encodes how this particular repository combines
files, registries, tests, policies, and verification for a recurring purpose.

## The product experience

From the developer's perspective, the interface remains a prompt:

```text
Natural-language intent
    → short probabilistic decision
        → capability instantiated as a deterministic operation
            → compact verified evidence
                → human-readable outcome
```

For novel work, the flow remains mostly agentic. For learned work, the model becomes a semantic controller:
it understands the request, chooses a trusted project capability, supplies parameters, and interprets the
evidence.

SEH is therefore not another coding agent. It is the deterministic engineering layer between the agent and
the repository: a versioned procedural memory that becomes more useful as the project and its developers
teach it recurring ways of working.
