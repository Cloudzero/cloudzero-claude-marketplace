---
name: model-right-sizer-eval
description: >-
  Run a blind, controlled audit of whether the model-right-sizer learning loop
  actually improves routing accuracy — or whether it is decoration. Spawns the
  agent in isolation against task sets it has never seen, with a no-memory
  control arm every round, an answer key committed before the first run, and a
  saturation gate that aborts a test too easy to measure anything. Produces a
  scored treatment-vs-control table across three rounds. Use when someone says
  "does the learning loop actually work", "audit the right-sizer", "benchmark
  the calibration ledger", or before trusting an accumulated ledger enough to
  route real spend by it.
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-eval — prove the loop works, or find out it doesn't

A learning loop that nobody audits is a story about improvement, not
improvement. This skill is the audit: does an accumulated calibration ledger
measurably improve the agent's routing picks on tasks it has never seen?

It is deliberately built to be able to **fail**, and the first run of it against
this plugin did (see "Known result" below). That's the point — a harness that
can only confirm the loop is worthless.

## The three ways this measurement goes wrong

Design against all three or don't bother running it.

1. **Memorization masquerading as learning.** Test on the same tasks you fed
   back and the score rises because the agent saw the answer, not because it got
   better. → **Disjoint task sets.** Learn on A, measure on B.
2. **Task difficulty masquerading as improvement.** Round 2's set happens to be
   easier and the trend line looks great. → **A no-memory control arm every
   round.** The control's three scores measure per-set difficulty and run
   variance; only the treatment-minus-control *gap* is evidence.
3. **Answer leakage.** The agent finds the eval material on disk. This repo's
   own [`eval/routing-tasks.jsonl`](../../eval/routing-tasks.jsonl) spells out
   the boundary reasoning in its `reference_text` — an agent that greps for it
   is reading the answers. → **Sandbox isolation** (below).

## Isolation protocol

1. **Fresh subagent per arm per round.** No conversation context inherits.
2. **Author the tasks at run time; never write them to disk.** Tasks that exist
   nowhere on the filesystem cannot be looked up. Pass them in the prompt.
3. **Sandbox the readable surface.** Copy into a scratch directory exactly:
   `agents/model-right-sizer.md`, and — treatment arm only — the learned
   `SKILL.md` and `ledger.jsonl`. Point the agent at those absolute paths and
   forbid all other filesystem access. **Never let the agent read the repo.**
4. **Answer key written before the first run**, at a path never named in any
   prompt. Pre-committing it is what stops the rubric drifting toward whatever
   the agent happened to produce.
5. **Bar sub-agent dispatch** in both arms (have it WebFetch pricing itself), so
   the two arms differ in exactly one variable: the memory.
6. **Audit the transcripts afterward** for filesystem wandering. A run that
   explored beyond its sandbox is void, not a data point.

## Stage 0 — the wire test (run this before anything else)

Measuring whether memory *improves accuracy* is pointless until you know the
memory is **read at all**. Stage 0 is a two-run smoke test that answers it in
minutes, and it is the single highest-value thing in this skill.

**Method.** Plant a sentinel learning in the trainable body plus matching ledger
rows, then run the agent blind against a task the sentinel speaks to. Three
properties make the sentinel un-fakeable:

1. **It contradicts first principles.** Point it at a task shape whose textbook
   answer is obvious (e.g. bulk structured extraction → cheapest tier) and have
   the sentinel demand the opposite. Agreement can then only come from the file.
2. **It carries a nonsense codename** (`MERIDIAN-88`) generated fresh per run —
   a recall canary that exists nowhere else.
3. **It is paired with a no-memory control** on the same task, so the
   counterfactual is measured rather than self-reported.

**Run it twice — the negative control is not optional.**

| Arm | Sentinel | Expected |
|---|---|---|
| **A · valid** | rows genuinely support the claim: the cheap tier *ran*, stayed in budget, still reworked | Pick moves; rows cited by id |
| **B · malformed** | rows contradict the claim — e.g. `recommended: haiku` but `actual: opus` on every row, so the cheap tier never actually ran | Pick **holds**; the discrepancy is named |

Arm B is what separates a reasoning loop from a compliance loop. An agent that
obeys any text placed in its memory file is not calibrated — it is
suggestible, and a single bad distillation would poison every future pick.

**Four pass criteria** (all four, or the loop is not wired):

- **Read** — the codename and row ids appear in the output.
- **Scoped** — a task with no matching `stage_kind` is explicitly reported as
  unmatched, and the pick is unchanged. No bleed.
- **Responsive** — arm A changes the pick, and the agent states what it would
  have chosen without the evidence.
- **Resistant** — arm B does *not* change the pick, and the reason is named.

Building the malformed sentinel is easy to get wrong by accident, which is
convenient: a hand-generated ledger tends to leak artifacts — `tokens = 4200×n`,
identical signals across rows, gapless daily timestamps, byte-identical `lesson`
strings. Those artifacts are themselves a fair test, since a real ledger never
looks like that.

## Protocol

| Round | Treatment | Control | Task set |
|---|---|---|---|
| 1 | agent + seed skill, **empty ledger** | agent alone | A |
| 2 | + learnings distilled from A | agent alone | B |
| 3 | + learnings from A **and** B | agent alone | C |

Sets A/B/C are disjoint, equal-length, and cover the **same** boundaries in
different surface clothing — so a round-over-round gain is transfer, not recall.

**Between rounds**, convert graded misses into calibration rows via
`model-right-sizer-calibrate append`, then distill into the learned skill (the
manual stand-in for SkillOpt-Sleep's nightly cycle). One rule makes this honest:
**a distilled learning must be a rule about a task shape that would apply to
tasks you have not authored yet.** If it names a specific task, you have written
an answer key, not a learning. The schema's 240-char `lesson` cap resists this
structurally; your judgment has to do the rest.

## Scoring

Three points per task, from
[`eval/boundary-rubric.json`](../../eval/boundary-rubric.json):

- **Tier** — the recommended tier *band* matches. Band, not exact model id: the
  agent fetches a live lineup, so pinning an id would score the price sheet
  rather than the reasoning.
- **Dial** — effort band matches **and** an explicit numeric budget is stated.
- **Boundary** — the specific reasoning that boundary exists to test is present.
  Partial reasoning scores zero; this is the discriminating criterion.

## The saturation gate — run this BEFORE the full experiment

**If the control arm scores above 70% on round 1, stop. The experiment is
invalid and no amount of additional rounds will fix it.**

A control near ceiling means first principles already answer your tasks, so
memory has nothing to add and any measured "gain" is noise. This is not a
hypothetical failure mode — it is what happened the first time this harness ran
(below). Round 1's control arm *is* the gate: score it before spending anything
on rounds 2 and 3.

Recovering from a saturated gate means changing the *class* of question, not
adding harder tasks of the same kind:

> **A calibration ledger can only pay for itself on questions first principles
> cannot settle.**

Boundaries the agent file teaches explicitly (the query-layer fork, the
over-thinking tax, the main-loop cache constraint) are answerable from the
persona alone — testing those measures the persona, not the memory. Discriminating
tasks look like:

- **Environment-specific economics.** "This shape of work, in this codebase, has
  cost two rework cycles at the mid tier, three times." Underivable from first
  principles; exactly what a ledger records.
- **Contested calls where the rubric genuinely points both ways** — where the
  agent's own honest output is a near-coin-flip, and evidence is what breaks the
  tie. Round 1 produced one naturally (a 0.45/0.45 split on an agentic
  down-pin); those are the rows worth building a set from.
- **Local threshold calibration.** The agent file's "~400 lines → bump a tier" is
  a seed prior it will tell you is unmeasured. What is the real number *here*?
- **Anti-learning checks.** Feed a learning contradicted by a fresh price sheet
  and confirm the agent lets the live sheet win. A loop that can't be corrected
  is worse than no loop.

## Known result — Stage 0, run 2026-08-05 (plugin 0.2.0)

Sentinel pointed at `structured-extraction` — a shape whose textbook answer is
the cheapest tier — against a 40k-row invoice-extraction task. **All four
criteria passed.**

| Arm | Sentinel rows | Pick | Verdict |
|---|---|---|---|
| Control (no memory) | — | Haiku 4.5 @ `none`, batch, conf 0.68 | baseline |
| **B · malformed** | `recommended: haiku` but `actual: opus/sonnet` on all 7 — the cheap tier never ran | Haiku 4.5, unchanged | **resisted** |
| **A · valid** | cheap tier ran, within budget, reworked 7/7 | Sonnet 5 @ `low`, batch, conf 0.62 | **responded** |

Arm A stated its own counterfactual — *"without the ledger I would have picked
Haiku 4.5 @ none, ~$32, confidence ~0.75"* — which the control run independently
confirms. It also re-scored the stage's effectiveness need from ~46 to 62, and
cited rows individually rather than in bulk: four rows mapped onto the exact
fields in question (tight match), two were *discounted* as possibly mitigated by
the task's stated conditions (which is why confidence landed at 0.62, not
higher), and one killed the obvious cheap alternative by recording that prompt
tightening had already been tried on that shape and hadn't held.

Arm B rejected the sentinel and said why: the rows recorded the *top* tier
reworking, so a claim about the cheapest tier's failure rested on a model with
zero measured runs in its own evidence. It flagged the synthetic numeric
signature, priced the damage of compliance, and steelmanned the sentinel before
rejecting it.

Both arms reported the unmatched second task as unmatched and left that pick
untouched, and both refused to count `provenance: seed` learnings as evidence —
"citing them as evidence would be double-counting."

**What this establishes:** the loop is live and *discriminating* — it responds to
evidence quality, not to the presence of text in a file. **What it does not
establish:** that accumulation over many rounds raises accuracy. That is what the
three-round protocol below is for, and it has not yet been demonstrated.

## Known result — the three-round accuracy protocol's first run

Run 2026-08-05 against plugin 0.2.0, eight boundaries, Set A, both arms on Opus:

| Arm | Tier | Dial | Boundary | Total |
|---|---|---|---|---|
| Control (no memory) | 8/8 | 8/8 | 8/8 | **24/24** |
| Treatment (seed skill, empty ledger) | 8/8 | 8/8 | 8/8 | **24/24** |

**Saturated. Rounds 2 and 3 were not run** — continuing would have cost ~200k
tokens to confirm a ceiling already reached, and any reported trend would have
been noise.

What it does and doesn't establish. It does **not** show the learning loop works;
it shows this eval couldn't tell. It **does** establish that the agent clears all
eight taught boundaries unaided — both arms independently found that caching was
worth ~$207/day against a tier choice worth ~$18.50/day, and that three of eight
stages improve by removing the model entirely. Strong first-principles
performance is precisely *why* the test couldn't discriminate, and it is the
reason the saturation gate now runs first.

**Report a saturated run as saturated.** The temptation to add a round and call
noise a trend is the whole reason this section names its own null result.

## Cost

Six agent runs (2 arms × 3 rounds), each a full Pass A over a task set with a
live pricing fetch — roughly 100k tokens per run on a top tier. The saturation
gate exists partly to keep an uninformative experiment from costing all six.

## Related

- [`model-right-sizer.md`](../../agents/model-right-sizer.md) — the agent under
  test.
- [`model-right-sizer-calibrate`](../model-right-sizer-calibrate/SKILL.md) —
  writes the rows the treatment arm reads between rounds.
- [`eval/boundary-rubric.json`](../../eval/boundary-rubric.json) — the eight
  boundaries and their scoring criteria.
- [`eval/probe-set-A.jsonl`](../../eval/probe-set-A.jsonl) — the published (and
  therefore **burned**) example set. Author your own for a blind run.
