---
name: model-right-sizer-release-report
description: >-
  Publish a per-version release report for `eval/token_ceiling_formula.py`
  every time `FORMULA_VERSION` bumps — the exact published configuration
  (preferred formula, signal weights, calibration constants), a ranked list
  of gaps for the next contributor, and what's explicitly settled and not
  worth re-relitigating. Its load-bearing rule, and the reason this skill
  exists as its own thing rather than folding into
  `model-right-sizer-research-report`: **every claim must interweave WHY it
  matters, in the same breath as WHAT changed** — a report is a version
  history if it just lists constants, but it stays a decision-support
  document only if a reader can tell, without opening a second file, what
  breaks (wasted spend, false over-budget alarms, undetected overruns, a
  silently re-biased fleet of budgets) if a given number or gap is wrong or
  ignored. Never a new-finding surface — like its sibling report skill, it
  synthesizes from already-committed `eval/tuning/results/` and
  `eval/ablation/results/` files, never runs new experiments. Also the
  designated tool for BACKFILLING a report for a past version that shipped
  before this skill existed, from that version's git history and whatever
  results files were live at the time. Use when someone says "write the
  release report for this version", "version the token ceiling formula",
  "what changed and why does it matter", "backfill a release report for
  v0.x", or after any `FORMULA_VERSION` bump.
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-release-report — a per-version record of what changed and why it matters

`eval/token_ceiling_formula.py` carries its own `FORMULA_VERSION`, independent
of the plugin-wide version and each skill's own, specifically so a consumer
can point at a stable reference instead of reading "whatever the file
currently says." This skill is what makes that version mean something: a
dated report, one per `FORMULA_VERSION` bump, that states the exact published
configuration, ranks the open gaps by expected value, and — the part a bare
changelog entry skips — says plainly what actually goes wrong if each number
or gap is wrong, ignored, or re-litigated for no reason.

**This is a synthesis skill, not a research skill**, the same discipline
`model-right-sizer-research-report` follows: it does not run new experiments,
dispatch a rating sub-agent, or generate a new data point. If a claim isn't
traceable to an already-committed results file or the module's own source,
it doesn't belong in the report.

## The rule this skill exists to enforce: every claim carries its stakes

A version report that lists `k = 0.5925` without saying what happens to a
fleet's worth of budgets if that number is 10% off is a changelog, not a
decision-support document — and this project already has a changelog
(`CHANGELOG.md`) for the "what shipped" record. This skill's report is for
the reader deciding how much to trust a number, escalate a gap, or spend the
next held-out task's scarce real-data budget — and that reader needs the
consequence stated next to the fact, not left as an exercise.

Concretely, every one of these gets its own "why this matters" clause,
woven into the prose immediately after the claim it explains (never a
separate "Why it matters" section bolted onto the end — see the shipped
v1.0.0 report at `eval/tuning/results/2026-08-22-token-ceiling-formula-v1.0.0-release.md`
for the target shape):

- **The preferred-formula choice** — what a wrong choice would let a future
  contributor silently reintroduce (e.g. the averaged model's proven capacity
  ceiling).
- **Every signal's weight, shipped or zero** — a zero-weight signal isn't
  neutral; it's a real lever nobody is pulling, and a shipped one is a real
  lever moving every prediction. Say which failure mode a wrong call on it
  produces (dilution, under-budgeting a specific task archetype, wasted
  dispatch budget re-discovering a settled result).
- **Every calibration constant** (`DISPATCH_FLOORS`, `REAL_WORK_SPAN`,
  `ADDITIVE_TOTAL_SPAN`, any calibration-status string) — what real dollar or
  trust cost a wrong value produces: false over-budget alarms that erode
  trust in the alarm itself, undetected overruns, a fleet-wide bias in one
  direction from a single mis-fit multiplier.
- **Every ranked gap** — not just what's missing, but the concrete failure it
  causes today while it stays open, and why it's ranked where it is relative
  to the other gaps (expected value, not just severity in isolation).
- **The settled/don't-re-relitigate list** — why re-testing a settled
  question is itself a cost (real dispatch tokens spent re-deriving a result
  this program already has, instead of on an open gap).
- **The version-history table** — why the bump-policy discipline (PATCH /
  MINOR / MAJOR, already documented in the module's own docstring) matters:
  it's what lets a future reader tell *when* ground truth changed under them
  and by how much, without diffing the source file by hand.

## Before starting

1. **Read the module itself first**:
   [`../../eval/token_ceiling_formula.py`](../../eval/token_ceiling_formula.py)
   — `FORMULA_VERSION`, `DISPATCH_FLOORS`, `REAL_WORK_SPAN`,
   `CALIBRATION_STATUS`, `ADDITIVE_TOTAL_SPAN`, `ADDITIVE_CALIBRATION_STATUS`,
   `SIGNAL_NAMES`, and each signal's own docstring paragraph (each already
   states its tested/untested/rejected status and cites the results file
   that proves it — don't re-derive what the module already says plainly).
2. **Diff against the previous version's report** (if one exists under
   `eval/tuning/results/*-release.md`) to scope what's actually new — a
   version report restates the full configuration every time (a reader
   shouldn't have to read three reports back to know the current signal
   weights) but the gap list and "why it matters" clauses should reflect
   what changed, not be copy-pasted forward unexamined.
3. **Read every results file the module's docstrings and gap list cite** —
   glob `../../eval/tuning/results/` and `../../eval/ablation/results/`
   rather than trusting a stale hand-maintained list. Pull exact numbers;
   never round or "reasonably infer" one that isn't stated.
4. **Check `../../eval/tuning/overfitting_guard.py`'s `HOLDOUT_TASKS`
   registry** for which held-out tasks exist and what they've already been
   used to check — this is where "confirmed once" vs. "confirmed twice" vs.
   "never tested against this archetype" claims get their exact count.

## What to do

1. **State the exact published configuration** — preferred formula, every
   signal's default weight and status, every calibration constant and
   status string — each claim immediately followed by its stakes clause per
   the rule above. This section should let a reader reconstruct the module's
   load-bearing constants without opening the source file.
2. **Rank the gaps by expected value**, each gap getting: what's missing,
   the concrete evidence that motivates ranking it here, why it matters in
   practice (the real failure it causes today), and a concrete next step —
   not "needs more research."
3. **State what's explicitly settled** — real evidence already answered
   this, re-testing without new task-shape evidence is a cost, not rigor.
4. **Keep or add a version-history table row** for this release, one line
   naming what changed since the prior version per the module's own bump
   policy (PATCH / MINOR / MAJOR).
5. **Publish as markdown, in-repo, dated** — `eval/tuning/results/<date>-token-ceiling-formula-v<version>-release.md`,
   matching this project's existing dated-results-file convention (this is
   NOT an HTML artifact like `model-right-sizer-research-report` — a version
   report is a durable, git-tracked reference other files cite by path, not
   a one-off executive readout). Add a `CHANGELOG.md` entry under
   `## Unreleased` pointing at the new report file.
6. **Offer, don't force, publishing a companion Artifact** — a version
   report reads fine as plain markdown for a contributor working in the
   repo, but if the requester wants a shareable/skimmable version (loads
   `artifact-design` first, calibrates to a document/spec-sheet treatment,
   not a landing page), that's a legitimate secondary output from the same
   content. The committed markdown file is always the canonical artifact;
   an HTML rendering is a view onto it, never the other way around.

## Backfilling a past release

If asked to backfill a report for a version that shipped before this skill
existed (or before any release report existed at all): reconstruct the
configuration AT THAT VERSION from git history (`git log -p` on
`token_ceiling_formula.py` to find the commit where a prior `FORMULA_VERSION`
was current, or from context if the module predates formal versioning) and
whatever results files existed as of that commit's date — never backfill
using CURRENT constants or gaps that didn't exist yet at that point in time.
A backfilled report's version-history table should note it was
reconstructed after the fact, and from what evidence, so a reader knows it
wasn't written contemporaneously.

## What this does NOT do

- It does **not** run any new experiment, dispatch any rating sub-agent, or
  generate a new data point — see `model-right-sizer-signal-validation`,
  `model-right-sizer-holdout-tuning`, and `model-right-sizer-layer-ablation`
  for that. This skill only reports on what already exists.
- It does **not** round, estimate, or "reasonably infer" a number that isn't
  actually stated in the module or a source results file.
- It does **not** soften a rejected signal, a placeholder calibration, or an
  unresolved split result to make the release look more finished than it is
  — "satisfactory" (every constant backed by *some* real evidence) and
  "finished" (every constant fully validated) are different claims, and the
  report says which one it's making.
- It does **not** replace `CHANGELOG.md` (the plugin-wide, all-files change
  log) or `model-right-sizer-research-report` (the condensed, chart-backed
  EXECUTIVE synthesis across the whole tuning program) — this skill is
  narrower and deeper: one module, one version, every claim's real-world
  stakes made explicit.

## Related

- [`../model-right-sizer-research-report/SKILL.md`](../model-right-sizer-research-report/SKILL.md)
  — the condensed, chart-backed executive synthesis across the *whole*
  tuning program (layer ablation, prompt tuning, holdout tuning, signal
  validation); this skill is narrower (one module, one version) and
  optimized for stakes-per-claim rather than a five-minute executive read.
- [`../model-right-sizer-signal-validation/SKILL.md`](../model-right-sizer-signal-validation/SKILL.md),
  [`../model-right-sizer-holdout-tuning/SKILL.md`](../model-right-sizer-holdout-tuning/SKILL.md),
  [`../model-right-sizer-layer-ablation/SKILL.md`](../model-right-sizer-layer-ablation/SKILL.md)
  — the experiment-running skills that close a gap this report ranks; a
  release report never runs these itself, only cites what they've already
  produced.
- [`../../eval/token_ceiling_formula.py`](../../eval/token_ceiling_formula.py)
  — the module this skill reports on; `FORMULA_VERSION`'s own docstring
  states the PATCH/MINOR/MAJOR bump policy this skill's version-history
  table follows.
- [`../../eval/tuning/results/2026-08-22-token-ceiling-formula-v1.0.0-release.md`](../../eval/tuning/results/2026-08-22-token-ceiling-formula-v1.0.0-release.md)
  — the v1.0.0 report, the reference shape for every "why it matters" clause
  this skill requires.
