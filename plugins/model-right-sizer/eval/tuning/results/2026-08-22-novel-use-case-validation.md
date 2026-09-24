# Novel-use-case validation — `repo-slack-channel`

Passes 1–5 tuned and scored `budget_margin=-1, effort_tax=1,
calibration_aggressiveness=1, calibration_decay=0, pass_b_feedback=1` entirely
against the benchmark's own synthetic tasks (`t1`–`t6`). This pass asks a
different question: **do these settled knobs generalize to a real,
previously-unseen task the benchmark never trained on?**

Task: the "Repo Slack Channel Routing" skill design
(`https://claude.ai/code/artifact/6101db3d-1af0-469a-b584-72736ef066f6`) — a
genuinely novel intent ("stand up and maintain a Slack channel for this repo")
with no synthetic-benchmark analog. The tuned variant was rendered to
`/tmp/.../scratchpad/tuned_variant.md` via `generate_variant.py` and used as
the model-right-sizer persona for both a dry-run (blueprint/routing decision)
and a real dispatch (actual sub-agent build) of one unit from that blueprint.

## Step 1 — dry-run: what the tuned agent actually routes

Given the artifact's intent, the tuned agent produced a 6-stage
`work_routing_map` (not hand-authored by me — this is the tuned model's own
output):

| unit | tier | budget (tokens) | loop_class |
|---|---|---:|---|
| `unit-channel-setup` | sonnet | 15,000 | low-tool-turn |
| `unit-message-prefilter` | haiku | 6,000 | single-shot |
| `unit-triage-classifier` | haiku | 8,000 | single-shot |
| `unit-ledger-status-lookup` | haiku | 6,000 | single-shot |
| `unit-proactive-event-poster` | sonnet | 12,000 | low-tool-turn |
| `unit-escalation-deepdive` | sonnet→opus (flip) | 40,000 | agentic |

Notable divergences from the source artifact's own suggested decomposition:
channel *provisioning* and *setup content* were merged into one Sonnet unit
rather than treated as a free/templated step, and `escalation-deepdive` was
added as a new agentic stage with an explicit Opus flip condition (deep
investigation of a repeated/ambiguous cost anomaly) that the artifact itself
didn't call out as a separate unit.

## Step 2 — real dispatch: `unit-channel-setup` at its own recommended tier

Rather than hand-build the skill, a real Sonnet-tier sub-agent was dispatched
against the tuned blueprint's own pick for `unit-channel-setup` (tier=sonnet,
budget=15,000). The sub-agent:

- Called `slack_search_channels` against multiple name variants and confirmed
  **no channel currently exists** for `cloudzero-claude-marketplace`.
- Enumerated its full available Slack MCP tool set and confirmed, correctly
  and without fabricating a workaround, that **no channel-creation tool
  exists** in this environment — a real capability gap, not a hypothetical
  one.
- Drafted real, README-grounded topic + pinned-intro-canvas content for the
  future channel (covering the `cost-analyst` and `model-right-sizer`
  plugins, install instructions, and channel purpose).
- Did **not** post anything live — there was no real target channel, and
  posting into an unrelated existing channel (e.g. `#ai-hub`) would have been
  scope creep beyond the assigned unit.

Real cost: raw=82,715 tokens, 9 tool uses, 36,550ms.

## Step 3 — scoring against the tuned budget

Using this session's characterized Sonnet zero-tool floor (40,669 tokens,
near-deterministic across probes):

```
net     = raw - floor = 82,715 - 40,669 = 42,046
ratio   = net / budgeted = 42,046 / 15,000 = 2.803
class   = classify_budget_adherence(2.803) = over_budget
```

## Result, stated plainly

**`over_budget` by ~2.8x.** The tuned settings' own `unit-channel-setup`
budget (15,000 tokens) undershot the real cost of a genuinely novel task by
nearly 3x. This is a legitimate generalization-test finding, not a benchmark
artifact to explain away:

- The benchmark's `t1`–`t6` tasks are synthetic and bounded; this task
  involved real tool calls (Slack search across several query variants) and
  real content generation (channel topic + full pinned canvas copy) that the
  benchmark's tuning loop never priced in.
- `effort_tax=+1` (this experiment's one clear positive result, first
  `within_budget` case in pass 4) was tuned against `t6`'s single bounded fix
  task. It does not, on this evidence, transfer to a multi-tool-call,
  content-generation-heavy unit like `unit-channel-setup`.
- This is consistent with a pattern visible across the whole tuning
  experiment: budgets tuned on synthetic single-shot/low-tool-turn tasks
  systematically underestimate real multi-tool-call agentic cost. It is the
  same shape of miss as `t1`'s exclusion (structurally too-small tasks) and
  `t4`'s decomposition explosion, just appearing on the *budget-magnitude*
  axis instead of the *decomposition* axis.

## What this does and doesn't invalidate

- It does **not** undo passes 3–4's within-benchmark findings — `budget_margin=-1`
  and `effort_tax=+1` are still the best-known settings *for this benchmark's
  own task distribution*, and the on-benchmark results (pass 4: accuracy
  0.0→1.0, first `within_budget`) stand as reported.
- It **does** mean this experiment's benchmark is not a reliable proxy for
  the model-right-sizer's overall budget-setting behavior on qualitatively
  different (real, multi-tool, content-heavy) work. A ceiling tuned tight
  against `t6`-shaped tasks is demonstrably too tight for `unit-channel-setup`-
  shaped ones.

## Honest scope note on this single data point

n=1: one real dispatch, one task. This is not a statistically powered
generalization test — it's a single real-world probe that surfaced a
directionally clear and fairly large miss (2.8x, not 1.1x). Repeating this
kind of out-of-benchmark spot-check on a few more genuinely novel tasks
before trusting these tuned settings in the shipped agent would be the
natural next step, not pursued in this pass.
