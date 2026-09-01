# agent-schema-families — a portable seam-shape catalogue

This is the **reusable catalogue** [`model-right-sizer-schema`](../skills/model-right-sizer-schema/SKILL.md)
picks from when it prescribes an output schema for one agent-to-controller
seam. It exists so that minimizing an agent's output doesn't mean inventing
a bespoke shape per agent — most agent replies are one of a small number of
recurring shapes (a review, a verdict, a report, a fetch, a wait, a plan),
and naming those shapes once means a new agent gets a schema by *picking a
family and filling its fields*, not designing one from a blank page.

**Provenance.** This is a portable, organization-agnostic distillation of a
seam-shape convention already used internally at CloudZero: a mandatory
`## Agent-to-agent schema` markdown stamp on every agent file, drawn from a
shared family catalogue, so an orchestrator recognizes a handful of
recurring shapes instead of relearning one bespoke schema per agent. This
file reproduces that same discipline in generic form — no internal tool
names, no named agents, no organization-specific fields — so any consumer
of this plugin gets the minimization benefit without depending on that
internal doc. **If the repo you're prescribing a schema for already has its
own catalogue** (a `context/agent-schemas.md`-shaped file, or an
equivalent), prefer *that* one — this file is the fallback for a repo that
doesn't have one yet, not a second taxonomy to reconcile against a first.

## The envelope every family lives inside

Every family below defines only the **`output.*`** payload. Wrap it in a
minimal envelope so the controller can branch on success/failure without
parsing prose:

```json
{ "status": "ok" | "error", "output": { "...family fields..." }, "error": { "reason": string } | null }
```

One field is common to every family, inside `output`:

- **`prose: string|null`** — the *one* bounded prose slot (≤150 words unless
  a family states otherwise). This is the typed home for judgment that
  genuinely needs sentences. It is a field, not a licence to attach a
  second, unbounded report alongside the typed one.

## Universal exclusion list

Applies to every family below — state it once here; an agent's own stamp
lists only its *additional*, agent-specific exclusions. Never inline, in
either direction of a handoff:

- Full conversation transcripts or chain-of-thought/deliberation narrative
- Raw tool output (diff bodies, API/MCP JSON, query result sets, log dumps)
- Full file contents — cite `path:line` instead
- Re-quoted upstream payloads — cite the reference that already holds them
- Secrets, API keys, environment values
- The agent's own persona preamble or "here's what I did" narration

## The families

| id | Family | Shape | Typical role |
|---|---|---|---|
| `scored-review` | Advisory quality lens | `scorecard[]` + `findings[]` + `leave_alone[]` | Grades a surface, returns fixable findings |
| `verdict-set` | Row-per-candidate adjudication | `rows[{subject, verdict, reason}]` + optional `gate` | A closed-enum verdict per item, sometimes gating a flow |
| `graded-claim` | A graded belief | `grade` + `evidence[]` + mandatory `counter_case` | "Is this true / worth pursuing" — never a bare verdict |
| `build-report` | One scoped unit, built | `files_changed[]` + `built[]` + `deferred[]` + `verification` | A coding/build agent's reply |
| `drafted-unit` | One scoped prose unit, written | `artifact_ref` + `sections_written[]` + `deferred[]` | A drafting agent's reply — the body lives on disk, never inline |
| `data-payload` | Fetched or computed rows | `rows_ref`/`findings[]` + `provenance[]` + `trust` | A fetch/query agent's reply, never its own interpretation |
| `watch-report` | A wait, resolved | `state` + `observed` + `elapsed_s` | Structurally excludes advice — there is no field for a recommendation |
| `action-log` | Mutations performed | `actions_taken[]` + `deferred[]` + `removed[]` | Any agent that mutates an external system (audit trail is the point) |
| `candidate-set` | Divergent generation | `candidates[]` + `frame`, no scores/verdict | The one family that structurally forbids judgment |

Reuse a family; coin a new one only when nothing here fits the seam's
actual shape — and when you do, keep the same discipline (typed fields, a
named exclusion list, at most one bounded prose slot).

### `scored-review`

```
output.target: string
output.scorecard: [{ dimension: string, score: number, ten_looks_like: string }]
output.findings: [{ id, dimension, severity: <agent-defined closed enum>,
                     location: string, claim: string, fix: string }]
output.leave_alone: [{ location: string, reason: string }]
output.prose: string|null
```
**Family exclusions:** the reviewed artifact itself (cite it, don't inline
it). A `findings[]` entry with no `fix` is a schema violation, not a soft
finding.

### `verdict-set`

```
output.scope: string
output.rows: [{ subject: string, verdict: <agent-defined closed enum>,
                 reason: string, evidence_ref: string }]
output.gate: { decision: <agent-defined closed enum>, one_line: string } | null
output.unresolved: [{ subject: string, why_unverifiable: string }]
output.prose: string|null
```
**Family exclusions:** the evidence bodies behind `evidence_ref` (cite,
don't inline). Never an unlisted verdict value — the enum is closed; a case
that doesn't fit goes in `unresolved`, never a new ad-hoc string.

### `graded-claim`

```
output.subject: string
output.grade: { score: number, confidence: <agent-defined closed enum> }
output.evidence: [{ source_ref: string, quote: string(<=40 words), stance: "supports"|"contradicts"|"complicates" }]
output.counter_case: string        # MANDATORY, non-empty
```
**Family exclusions:** full transcripts behind `source_ref` (quote ≤40
words, then cite). A verdict shipped with no `counter_case` is this
family's own failure mode.

### `build-report`

```
output.unit_id: string
output.files_changed: [{ path, kind: "added"|"modified"|"deleted", summary }]
output.built: [string]
output.deferred: [{ item, why }]
output.verification: { command: string, result: "pass"|"fail"|"not-run" }
```
**Family exclusions:** the diff itself — the files are on disk; the
consumer reads them there. No code blocks, no test stdout (cite
`verification.command`).

### `drafted-unit`

```
output.unit_id: string
output.artifact_ref: string        # path — NEVER the drafted body inline
output.sections_written: [string]
output.deferred: [{ item, why }]
```
**Family exclusions:** the draft body itself — always by `artifact_ref`,
never inlined (the single largest token leak this family is prone to).

### `data-payload`

```
output.query: { what: string, params: object }
output.rows_ref: string            # reference — bulk rows never inline
output.row_count: number
output.provenance: [{ source, as_of }]
output.trust: <agent-defined closed enum>
```
**Family exclusions:** bulk rows above ~20 always go to `rows_ref`, never
the message body. Any credential. Any interpretation of the data — that's
the caller's lens, not this agent's.

### `watch-report`

```
output.condition: string
output.state: <agent-defined closed enum, e.g. "MET"|"TIMED_OUT"|"ERRORED">
output.observed: { last_seen: string, value?: any }
output.elapsed_s: number
output.prose: null                 # this family carries no prose slot by default
```
**Family exclusions:** recommendations or next-step advice — no field
exists for them; that's structural, not a style choice. Poll logs or
per-cycle narration.

### `action-log`

```
output.actions_taken: [{ action, subject, result, reversible: bool }]
output.deferred: [{ action, subject, why }]
output.removed: [{ subject, proof }]
```
**Family exclusions:** command/API output (cite the action, not its
stdout). Never an `actions_taken` entry without `result`; never a `removed`
entry without `proof`.

### `candidate-set`

```
output.frame: string               # the vantage this branch ran under
output.candidates: [{ text: string(<=1 sentence), rationale: string(<=25 words) }]
output.prose: null                 # NO prose slot — prose is where evaluation leaks in
```
**Family exclusions:** scores, rankings, confidence values, hedges, and any
reference to another branch's candidates — all of that belongs to the
consuming critic; a branch that emits it has broken the isolation this
family exists to protect.

## Two composable extensions

Not families themselves — compose onto any family's `output` when the
agent has the corresponding shape:

| Extension | Adds |
|---|---|
| `+mode` | `mode: <closed enum>` — required, first field, for an agent that runs more than one distinct pass (e.g. a before/after bookend) |
| `+writes` | `artifacts: [{ path, kind, summary }]` — every file this run created or modified |

## Worked example — the per-agent stamp

The shape [`model-right-sizer-schema`](../skills/model-right-sizer-schema/SKILL.md)
produces, filled in for a hypothetical log-triage agent (family
`scored-review`):

```markdown
<!-- model-right-sizer-schema:begin — family definitions, the universal exclusion
     list, and the no-freelancing rule are single-sourced in
     schemas/agent-schema-families.md. Fields below are THIS agent's; never
     restate the shared discipline here. Re-run model-right-sizer-schema to
     refresh. -->
## Agent-to-agent schema

**Family:** `scored-review` · **`task_type:`** `log_triage` · **v1.0**

**In** — `logs_ref: string` (a reference to the log source, never the raw
lines) · `window: string` · `budget_tokens: int`

**Out** — the `{status, output, error}` envelope; `output.*`:
`target: string` ·
`scorecard: [{dimension: enum[error-rate, novelty, blast-radius], score: 1-10, ten_looks_like: string}]` ·
`findings: [{id, dimension, severity: enum[P1, P2, hygiene], location: "service:line", claim: string, fix: string}]` ·
`leave_alone: [{location, reason}]` ·
`prose: string|null` (≤150w, the on-call-relevant summary)

**Never inline (this agent, beyond the universal list):** raw log lines ·
stack traces (cite `location` instead) · prior triage runs' full reports.

You return ONLY this schema — no prose channel alongside it; the one bounded
prose slot is the whole allowance. If the shape genuinely can't hold a finding,
return `status: "error"` rather than freelance into prose.
<!-- model-right-sizer-schema:end -->
```

## Related

- [`../skills/model-right-sizer-schema/SKILL.md`](../skills/model-right-sizer-schema/SKILL.md) —
  the skill that picks a family from here (or the repo's own catalogue, if
  it has one) and stamps it onto a target agent.
- [`agent-schema.schema.json`](agent-schema.schema.json) /
  [`agent-schema.example.json`](agent-schema.example.json) — the strict JSON
  contract for the *prescription* this skill's agent dispatch must emit
  before any stamp gets written.
- [`blueprint.schema.json`](blueprint.schema.json) — the sibling contract
  for a whole flow's routing blueprint; `message_schemas[]` there is this
  same discipline applied to a multi-stage chain instead of one seam.
