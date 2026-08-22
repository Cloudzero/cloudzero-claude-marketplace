# Breaking down token consumption by sub-agent archetype, and deriving signals from it

Direct follow-up to "break down the key factors that affect token
consumption in each sub agent and let's derive signals for those." Every
prior signal (`tool_call_volume`, `content_volume`, `cross_reference_load`,
`validation_loop_iterations`) was derived from **one task's six build
units** — a single task SHAPE. The gap that leaves: those signals were
never checked against sub-agent archetypes that look nothing like "edit a
file in an existing repo." This document works the other direction —
starting from the archetypes `agents/model-right-sizer.md` itself names a
blueprint decomposing into (`build stage, review stage, QA fan-out,
synthesis/panel stage, finder → verifier fan-out, query-shaped stage`) —
and asks what actually drives each one's token spend, before proposing
what's still missing.

## Grounding: what actually consumes tokens, structurally

The agent's own "Economic formalization" section names the cost function
`TC = P_k·K + P_m·M + w·L`, where `M` = "reasoning + tool-call spend."
Unpacked, `M` for any single sub-agent dispatch decomposes into exactly
four structural buckets, regardless of archetype:

1. **Input tokens read before producing anything** — the prompt, any
   pre-existing material the unit must ingest to do its job.
2. **Tool-call round-trip tokens** — every search/edit/re-run and the
   tokens spent reasoning about what to call next and interpreting what
   came back.
3. **Output tokens produced** — the actual content/edits/prose generated.
4. **Iteration tokens** — repeats of (1)-(3) triggered by a failed
   check, a self-correction, or a validate-then-fix loop.

`tool_call_volume` ≈ bucket 2. `content_volume` ≈ bucket 3.
`validation_loop_iterations` ≈ bucket 4. `cross_reference_load` is a
*specific* slice of bucket 1 — pre-existing material read **because it
must be stayed consistent with**, not all input-reading. That's the seam
this document's gap-finding hangs off.

## Per-archetype breakdown

| Archetype (from `model-right-sizer.md`'s own decomposition list) | Dominant token drivers | Best-covered by | Weakly covered / gap |
|---|---|---|---|
| **Build/implementation unit** (writes or edits code/content — this pass's own 6 training units are all this archetype) | Output volume; cross-referencing sibling artifacts; occasional validate-fix loop | `content_volume`, `cross_reference_load`, `validation_loop_iterations` | Bucket 1 when the unit edits *inside* a large pre-existing file it must read in full but isn't required to stay consistent with (a big legacy module, one small fix) — no existing signal separates "large context, low consistency burden" from "small context, high consistency burden," and those are genuinely different cost shapes |
| **Review/QA unit** (reads a diff or artifact and produces a verdict) | Input volume (the diff/artifact itself) dominates; output is typically short (findings list); tool calls are usually a handful of reads, not iteration | `content_volume` (correctly low), `tool_call_volume` (correctly low) | Input-reading bucket is *the* cost driver here and nothing scores it directly — a large diff costs tokens whether or not there's anything to cross-reference against |
| **Finder/discovery unit** (search across a codebase/dataset for something not known in advance) | Tool-call round-trips dominate, but *how many turns until convergence* depends on how well-specified the target is, not just on "does it use tools" | `tool_call_volume` (captures volume, not convergence risk) | Open-endedness — a finder told exactly what pattern to grep for converges in 1-2 calls; one told "find the mid-turn token signal, if one exists" (this pass's own skill-authoring unit) can burn many exploratory turns hunting a negative result. `tool_call_volume` alone can't distinguish "5 calls because the target is well-specified and needs 5 lookups" from "5 calls because the first 4 were dead ends" |
| **Synthesis/judge/panel unit** (aggregates N inputs into one verdict) | Input volume scales with N (every finding/candidate it must read); output is a synthesis, not raw content | `cross_reference_load` (partially — it does read several other artifacts) | Fan-in volume is closer to "N things to reconcile," which `cross_reference_load`'s definition ("stay faithful to several other artifacts") already gestures at, so this archetype is reasonably covered as-is — flagged here as a confirmation, not a gap |
| **Query-shaped unit** (lookup/join/aggregate over structured data) | Should route around a model entirely (`model: "deterministic_query_layer"`, `token_ceiling: 0`) | N/A — `query_shaped: true` already short-circuits the whole signal system per the schema | None — this archetype correctly exits the signal-rating question altogether; listed here so the table is a complete accounting of the decomposition list, not because it needs a new signal |

## What's actually missing, derived from the table, not invented abstractly

Two gaps repeat across *multiple* archetypes above (build units editing
inside large legacy material, review units reading a large diff, finder
units with a genuinely open-ended target) — that repetition, not any
single task's shape, is the bar for proposing a new signal, per this
pass's own standard ("does it separate examples the current signals
can't, not just correlate with one that's already there").

### Candidate 1 — `context_ingestion_volume`

**Definition:** how much *pre-existing* material (a file, a diff, a prior
handoff) this unit must read and hold in context before producing
anything, independent of whether it must stay *consistent* with that
material. 0.0 = works from a short prompt with no meaningful pre-existing
material to ingest; 1.0 = must read and hold a large body of existing
content before acting at all.

**Why it's distinct from `cross_reference_load`:** `cross_reference_load`
asks "how many other artifacts must this unit's OUTPUT stay faithful to."
`context_ingestion_volume` asks "how much must this unit READ first,"
full stop — a review unit reading a 2,000-line diff to produce a 10-line
verdict has near-zero cross-referencing (nothing downstream to stay
consistent with) but high ingestion cost; a build unit making a one-line
fix inside a small, already-fully-understood file has near-zero ingestion
cost. These two units would score identically on the three existing
signals today and cost very differently in bucket 1 tokens.

**Most load-bearing for:** review/QA units, and build units editing
inside large pre-existing files.

### Candidate 2 — `investigative_uncertainty`

(Carried over from `2026-08-22-additive-formula-and-signal-expansion.md`'s
proposed list, now grounded against a second archetype rather than one
task's guess.) **Definition:** whether this unit's tool-call sequence is
searching for something whose existence or shape isn't known going in
(open-ended research, "does X exist — if so, what shape") vs. executing
an already-fully-specified sequence of calls. 0.0 = every tool call's
target is already known before dispatch; 1.0 = genuinely open-ended
search where most calls are exploratory and some will be dead ends.

**Why it's distinct from `tool_call_volume`:** `tool_call_volume` scores
*how many* calls; this scores *how likely each call is to be a
productive step toward the goal vs. a dead end.* Two finder units can both
score 0.6 on `tool_call_volume` (a moderate number of calls) while one
converges in exactly that many calls because the target was well-specified
and the other burns half of them on dead ends because it wasn't — same
call count, different cost efficiency, and the difference is knowable
*before* dispatch from how the task is specified.

**Most load-bearing for:** finder/discovery units, and the exploratory
phase of synthesis/judge units before they have enough inputs to
reconcile.

## What is deliberately NOT proposed here, and why

`shared_file_blast_radius` and
`voice_or_precision_consistency_requirement` (also from the prior
proposal list) are not re-proposed alongside the two above. Both are
real, but neither showed up as a *repeated* gap across the archetype
table the way ingestion volume and investigative uncertainty did — they
were originally reasoned from this pass's own six units, the exact thing
this document exists to check against a wider set of shapes. Per
`validation_loop_iterations`'s own result (plausible on paper, measured
to dilute rather than help), a signal earns a place in this list by
showing up as a gap independently, not by sounding right. Two well-argued
candidates, tested properly, are worth more than four untested ones —
this is a `Less is More` call, not an oversight: adding signal count
before evidence justifies it is exactly the failure mode
`validation_loop_iterations` already demonstrated once this pass.

## What happens next — and explicitly does NOT happen yet

Following this pass's own established discipline (validated once already
on `validation_loop_iterations`, and the explicit user choice earlier in
this pass to "test signal-rating reliability first"):

1. **Neither candidate is wired into `token_ceiling_formula.py`'s API
   yet.** Both need a real definition test — a fresh, independently-rated
   multi-draw pass — the same bar `validation_loop_iterations` was held
   to, before touching signatures or defaults.
2. **The test data this time should NOT be the same six chief-of-staff
   units again.** The entire premise of this document is that those six
   units are all one archetype (build/implementation); testing a
   finder/discovery-shaped signal like `investigative_uncertainty` against
   build-only data would validate nothing about the archetype it's
   actually meant for. The next real step is real dispatch data from a
   review unit and a finder unit specifically — not another pass over the
   same retired build-unit numbers.
3. **`context_ingestion_volume` is the cheaper one to validate first** —
   it's checkable against data this pass may already be able to
   approximate (input size is often directly measurable, unlike a
   judgment-call rating) before spending a rating pass on it.

No schema change, no default-weight change, and no new training data
collection happened in this document — it's the breakdown and the
candidate derivation the user asked for, staged for the same
validate-before-integrate pipeline every other signal in this pass went
through.
