---
name: model-right-sizer-calibrate
description: >-
  Feed and read the machine-wide `model-right-sizer` calibration ledger — the
  memory that keeps every right-sizing blueprint from starting at zero. Three
  modes: `append` turns a Pass B usage report into schema-valid, repo-agnostic
  ledger rows and appends them; `summary` aggregates the ledger by task shape
  so Pass A has evidence to read even before any distillation has run; `review`
  shows a SkillOpt-Sleep staged proposal against the current learned skill and
  adopts it only on explicit approval. Enforces the repo-agnostic contract —
  rows record task SHAPES (stage_kind, loop_class, signals,
  recommended-vs-actual, rework cycles), never repo names, paths, ticket ids,
  code, or customer data — because the ledger is read in every repo on the
  machine. Use when someone says "log this run", "append the calibration",
  "what has the right-sizer learned", "show the ledger summary", or "review the
  staged skill proposal".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-calibrate — feed and read the calibration ledger

The [`model-right-sizer`](../../agents/model-right-sizer.md) agent is read-only
by design: it reasons, scores, and reports, but it never writes. That leaves a
gap at both ends of its bookend — Pass A wants a calibration history to read,
and Pass B produces calibration rows nobody persists. **This skill is the
write half.** It is the only sanctioned way evidence enters the ledger.

## Where the artifacts live, and why they're outside every repo

```
~/.claude/skills/model-right-sizer-learned/
├── SKILL.md                  distilled learnings (gate-validated prose)
├── ledger.jsonl              append-only evidence, one JSON row per line
└── eval/routing-tasks.jsonl  held-out gate set
```

Machine-wide, not per repo, for one reason: the agent's core job is pricing the
**cost of error**, and that price is only knowable from what past picks actually
cost. Siloed per repo, that evidence never reaches the sample size where it
means anything. Stored once, a calibration measured on one codebase sharpens the
pick made on the next.

The price of that reach is a hard constraint: **a row records a task shape, not
a task.** No repo names, file paths, branch/PR/ticket ids, code snippets,
customer or account data, or workspace proper nouns. [`ledger-entry.schema.json`](../../templates/ledger-entry.schema.json)
constrains the *shape* — `additionalProperties: false` everywhere rejects
unknown keys, `stage_kind` is a closed vocabulary, `lesson` is capped at 240
characters (prose long enough to narrate a specific incident is prose long
enough to identify it).

**But schema validation is not content sanitization, and conflating the two is
how a leak ships.** `lesson` and both model fields accept arbitrary strings, so
a row naming a repo is still perfectly schema-valid. The redaction check in
step 4 below is the *only* control covering free text on append, and
`model-right-sizer-verify`'s INTEGRITY pass is the only one covering it after
the fact. Neither is enforceable by the schema. A green validation means the
row is well-formed — never that it is repo-agnostic.

If the paths above don't exist, the loop was never installed. Create them and
proceed — this skill is self-healing — then mention that
[`model-right-sizer-install`](../model-right-sizer-install/SKILL.md) sets up the
rest (the mandate blocks, and the optional nightly distillation).

## Mode: `append` (the default)

Turn a Pass B usage report into ledger rows.

1. **Take one row per stage that spent real tokens.** Not per file, not per
   turn. A stage the report doesn't cover doesn't get a row.
2. **Build each row against the schema.** Read
   [`ledger-entry.schema.json`](../../templates/ledger-entry.schema.json) — it
   is the authority, not this file's summary of it. Required:
   `id` · `ts` (date only) · `stage_kind` · `loop_class` · `signals` ·
   `recommended` · `actual` · `outcome` · `verdict` · `lesson`. Optional but
   valuable when measured: `adherence`, `cost_delta_usd` with its
   `pricing_freshness` tag, `rework_cycles`, `tool_turns`, `wallclock_s`.
3. **Omit what you didn't measure — never estimate into the ledger.** An
   invented token count or a guessed wall-clock reading doesn't just make one
   row wrong; it poisons every future pick that reads that row, and it is
   indistinguishable from a real measurement afterward. A sparse honest row
   beats a complete fabricated one. This is the single most important rule in
   this skill.
4. **Run the redaction check before writing.** Reject and rewrite any row
   containing: a repo or directory name, a file path, a branch/PR/issue/ticket
   id, a code snippet or identifier lifted from the work, a customer or account
   name, or a person's name. Map the work onto the closed `stage_kind`
   vocabulary instead — if nothing fits, pick the nearest shape and say so in
   the `lesson`; do not invent an enum value, and do not smuggle specificity
   into the free-text field to compensate.
5. **Assign `id` as the next `cal-NNNN`** after the highest already in the
   ledger (starting at `cal-0001`), and set `ts` to today's date.

   **Allocate the id under a lock — concurrent sessions are the normal case
   here, not an edge case.** This ledger is machine-wide by design, so two
   sessions in two different repos writing within the same minute is expected
   behaviour. Read-highest-then-append is a classic race: both read `cal-0006`,
   both write `cal-0007`, and every later citation of `cal-0007` becomes
   ambiguous — which quietly corrupts provenance, the one property the ledger
   exists to provide.
   - Take an exclusive lock on a sibling lockfile (`ledger.lock`) for the whole
     read-max → write sequence, and release it even on failure.
   - **Verify after writing**, always: re-read the tail and confirm your id
     appears exactly once. If it appears twice, a writer without the lock beat
     you — rewrite *your* row with the next free id and say so.
   - If you cannot take a lock in your runtime, still do the post-write
     verification. Detecting the collision and renumbering is the part that
     preserves the audit trail; the lock only makes it rare.
6. **Append, never rewrite.** One JSON object per line, appended to
   `ledger.jsonl` in a single atomic write (open in append mode; do not
   read-modify-write the whole file). Never reformat, reorder, or edit existing
   rows — the file is an audit trail. If a past row is wrong, append a corrected
   one and say so in its `lesson`. The one exception is the collision
   renumbering in step 5, which fixes a row you just wrote in this run.
7. **Echo what you wrote** and confirm the new row count.

If a row can't be made schema-valid, say why and skip it rather than writing a
malformed line — one bad line breaks every reader of the file.

## Mode: `summary`

Aggregate the ledger into something Pass A can act on. This is what makes the
loop useful on **day one**, long before any distillation has run.

Read `ledger.jsonl` and report, grouped by `stage_kind`:

- row count, and how many are recent enough to trust;
- the split of `verdict` (`size-up` / `size-down` / `keep` /
  `route-to-query-layer` / `measurement-required`);
- `outcome.quality` distribution and total `rework_cycles` — the cost-of-error
  signal;
- mean `cost_delta_usd`, tagged with the weakest `pricing_freshness` in the
  group (a mean over stale prices is a stale mean, and should be labeled one);
- budget and schema adherence counts;
- **any duplicate `id`** — the signature of a concurrent-append race that beat
  the lock. Report them explicitly rather than silently deduping: a duplicate id
  makes every citation of it ambiguous, and the operator needs to know which
  rows to renumber.

Then state the actionable read in one line per shape — e.g. *"`code-review`:
6 rows, 4 size-up, 3 with rework ≥ 2 → this shape is being under-powered."*

**Say the sample size out loud, every time.** Two rows are an anecdote. Report
them as an anecdote rather than a trend, and never let a thin group's mean sound
like a finding.

## Mode: `review`

Review and adopt a SkillOpt-Sleep staged proposal for the learned skill.

1. `skillopt-sleep status` to see whether a proposal is staged. Not installed,
   or nothing staged → say so and stop; nothing here is broken, the loop just
   hasn't produced a proposal.
2. **Show the actual diff** against the current `SKILL.md` — the specific added,
   changed, and deleted learnings, not a summary of them.
3. **Check the protected regions survived.** The proposal must not have touched
   `<!-- SLOW_UPDATE_START -->…<!-- SLOW_UPDATE_END -->` or
   `<!-- APPENDIX_START -->…<!-- APPENDIX_END -->`. If it did, that's a defect
   in the run — report it and do not adopt.
4. **Sanity-check the content against the same bar as an appended row**: is each
   new learning repo-agnostic, and is it supported by rows actually in the
   ledger? A learning the evidence doesn't support is worse than no learning,
   because it will be cited with the authority of a measurement.
5. **Adopt only on an explicit yes** (`skillopt-sleep adopt`). Never
   auto-adopt — a validation gate is evidence, not consent. On a no, leave the
   proposal staged and say what would need to change.

## What this skill does not do

- It does **not** make right-sizing picks — that's the agent's job. This skill
  records what happened and reports the aggregate.
- It does **not** hand-edit the learned skill's distilled prose. Evidence enters
  as rows; prose changes come through `review`. (Hand-editing is possible and
  sometimes reasonable — it's just unaudited, so prefer the loop.)
- It does **not** install SkillOpt or schedule anything — that's
  [`model-right-sizer-install`](../model-right-sizer-install/SKILL.md) step 6,
  and it's optional.
- It does **not** touch the repo you're working in. Its only writes are the
  ledger and — on explicit approval in `review` — the learned skill.

## Related

- [`model-right-sizer.md`](../../agents/model-right-sizer.md) — Pass A step 8
  reads what this skill writes; Pass B emits the rows it appends.
- [`model-right-sizer-install`](../model-right-sizer-install/SKILL.md) — seeds
  the artifacts this skill maintains.
- [`model-right-sizer-dryrun`](../model-right-sizer-dryrun/SKILL.md) — the
  blueprint-only preview, which reads the ledger but never writes to it.
