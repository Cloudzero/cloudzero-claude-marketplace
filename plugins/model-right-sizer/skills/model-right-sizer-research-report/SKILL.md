---
name: model-right-sizer-research-report
description: >-
  Package up every result this plugin's tuning/validation research has
  produced — the layer-ablation study (`eval/ablation/`), the prompt-tuning
  coordinate-ascent passes and the dispatch-floor-awareness/held-out-task
  work (`eval/tuning/`), the averaged-vs-additive `token_ceiling_formula.py`
  pivot, and the real-work-signal validation experiments — into one
  condensed, research-paper-style EXECUTIVE report with real charts, built
  entirely from the numbers already recorded in this repo's own dated
  results files (never invented or rounded up). Publishes a self-contained
  HTML report (loads the `dataviz` and `artifact-design` skills first) with
  an abstract, a key-findings table, a handful of figures, limitations
  stated as prominently as wins, and a reproducibility appendix pointing at
  the companion skills that can re-run each experiment
  (`model-right-sizer-layer-ablation`, `model-right-sizer-prompt-tuning`,
  `model-right-sizer-holdout-tuning`, `model-right-sizer-signal-validation`).
  Use when someone says "write up all the tuning results", "executive
  summary of the research", "package the findings into a report",
  "research report with charts", or "summarize everything we've found so
  far for leadership".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-research-report — condense the tuning research into an executive report

This plugin's research trail is large and scattered across many dated
files (16+ results files under `eval/tuning/results/`, two under
`eval/ablation/results/`, two `DESIGN.md` narratives, and the source
modules those files report on) — accurate, but not something an executive
reads end to end. This skill's whole job is the compression: read
everything, extract only what's load-bearing, and produce one short,
chart-backed report that states real findings — including the rejected
and null ones — without re-litigating the full narrative.

**This is a synthesis skill, not a research skill.** It does not run new
experiments, dispatch sub-agents, or generate new data — it reports on
data that already exists in this repo. If a finding isn't traceable to a
specific already-committed file, it doesn't belong in the report.

## Before starting

1. **Load `dataviz`** before writing a single chart. Its six-check color
   validator, form heuristic, and mark specs are not optional polish —
   run the palette validator before shipping any chart this skill
   produces.
2. **Load `artifact-design`** before writing the HTML file. Calibrate how
   much design investment an executive research report warrants (this is
   a real deliverable with an audience, not a throwaway) before writing
   markup.
3. **Read the full source inventory** (don't sample a few files and
   extrapolate):
   - [`../../eval/ablation/DESIGN.md`](../../eval/ablation/DESIGN.md) +
     everything under `../../eval/ablation/results/`
   - [`../../eval/tuning/DESIGN.md`](../../eval/tuning/DESIGN.md) +
     everything under `../../eval/tuning/results/` (glob it — new files
     are added faster than this list can be hand-maintained)
   - [`../../eval/token_ceiling_formula.py`](../../eval/token_ceiling_formula.py),
     [`../../eval/tuning/knobs.py`](../../eval/tuning/knobs.py),
     [`../../eval/tuning/weight_optimizer.py`](../../eval/tuning/weight_optimizer.py),
     [`../../eval/tuning/overfitting_guard.py`](../../eval/tuning/overfitting_guard.py)
     — the source-of-truth constants/verdicts behind the write-ups
     (`CALIBRATION_STATUS`, `ADDITIVE_CALIBRATION_STATUS`, `HOLDOUT_TASKS`,
     each signal's tested/untested status)

## What to do

1. **Build a findings ledger before writing any prose.** For every
   distinct experiment (each dated results file, or each named DESIGN.md
   section for ones without a standalone file), extract as structured
   data: `{name, date, question asked, headline metric before → after,
   verdict (adopted / rejected / promising-not-proven / structural
   finding), source file}`. This ledger is the report's spine — every
   sentence in the sections below should trace back to a row in it. Do
   not proceed to writing charts or prose from memory of what a file
   "probably said" — pull the exact numbers.
2. **Group the ledger into the report's narrative arc**, chronological
   and causal, not just a flat list:
   - **Layer ablation** — does each of the four research-grounded
     citation layers change anything, alone and combined? (`eval/ablation/`)
   - **Prompt-tuning coordinate ascent** — wording knobs tuned against a
     synthetic benchmark, including the two measurement-breakdown
     corrections (t1's per-item ceiling gap, t6's floor-noise
     misdiagnosis) — negative findings that are themselves real results.
   - **Held-out-task tuning** — `dispatch_floor_awareness`'s climb from
     level 0 to 3 against real actuals, level 4 and 5's rejection, and the
     single-draw-noise correction (0.333 → the true 0.167) that reset how
     the whole program measures anything after it.
   - **The `token_ceiling_formula.py` pivot** — from free-hand integers to
     rated signals; the averaged model's PROVEN capacity ceiling (≤16.7%,
     provable before training, confirmed by a gradient-checked run); the
     additive model's structural fix (94.4%) and the single-scalar
     overfitting check that caught it; `ADDITIVE_CALIBRATION_STATUS`'s
     honest `UNVALIDATED` label.
   - **Real-work-signal validation** — `validation_loop_iterations`
     (tested, rejected: dilutes), `context_ingestion_volume` (tested,
     rejected: dilutes, confirmed on genuinely blind data),
     `investigative_uncertainty` (promising, not yet proven — the one
     candidate whose combined-sum correlation improved), and the
     contamination catch itself (self-authored "blind" draws in a context
     already holding the answer produced a fabricated-looking r=0.989,
     caught and discarded before it reached a weight).
3. **Write the report in this shape** — condensed research-paper
   register, not the underlying docs' full narrative voice:
   - **Title + one-line subtitle.**
   - **Abstract** (4–6 sentences): what was studied, the method in one
     clause, the two or three headline results, stated plainly including
     the negative ones — an abstract that only reports wins is not
     honest to this research program's actual shape.
   - **Key Findings table**: ~6–10 rows, `{finding, evidence, verdict}` —
     scannable in under a minute. Include structural findings (the
     capacity-ceiling proof), adopted changes (the additive formula), AND
     rejected candidates (both failed signals, both rejected knob levels)
     with equal visual weight — a rejected/negative finding is not a
     lesser row.
   - **Methodology** (one short paragraph): the overall arc — ablate →
     tune wording against synthetic tasks → tune against real held-out
     actuals → restructure the aggregation formula → validate new signals
     blind — and the recurring discipline that runs through all of it
     (never trust a single draw; never fit and validate against the same
     numbers; dispatch genuinely independent raters, not self-authored
     ones).
   - **Results**, one subsection per narrative group from step 2, each
     with 2–4 sentences of prose and exactly one figure (step 4) — resist
     the underlying docs' full derivations; link to the source file for
     anyone who wants the proof.
   - **Limitations**, stated as its own first-class section, not a
     footnote: small-n throughout (most real-actuals comparisons are
     n=6, one task); `ADDITIVE_TOTAL_SPAN`'s `UNVALIDATED` status; opus
     and haiku tiers' calibration is placeholder-only (scaled by floor
     ratio, not independently measured); the self-authored-draw
     contamination risk this program already found once and is now
     actively guarding against, not something to claim is fully solved.
   - **Recommendations / Next Steps**: 2–4 concrete next moves, each
     tied to a specific companion skill (a fresh held-out task via
     `model-right-sizer-holdout-tuning`; a second held-out-task check for
     `investigative_uncertainty` via `model-right-sizer-signal-validation`;
     etc.) — not vague "continue researching" language.
   - **Reproducibility appendix**: name every companion skill that can
     re-run part of this research (`model-right-sizer-layer-ablation`,
     `model-right-sizer-prompt-tuning`, `model-right-sizer-holdout-tuning`,
     `model-right-sizer-signal-validation`) and, in one line each, what
     it re-runs and what ground truth it needs.
4. **Figures — build from real numbers, cite the source file in the
   caption.** A suggested set (adjust to whatever the ledger actually
   supports; don't force a chart where the underlying data doesn't
   support one):
   - Accuracy-rate progression across the held-out-task tuning passes
     (dispatch_floor_awareness levels), annotated where the single-draw
     0.333 was later corrected to the true 0.167.
   - Averaged-model vs. additive-model training accuracy (the ~16.7% vs.
     94.4% structural-fix finding) — this is the single most
     visually-striking finding in the whole program and deserves a clear
     bar chart.
   - Per-signal noise (CV%) across the signal-validation experiments,
     including the visible drop between the self-authored and genuinely
     blind draws — itself a finding worth showing, not hiding.
   - Correlation-with-real-cost delta for each tested candidate signal
     (baseline vs. baseline+candidate) — the chart that makes
     "dilutes vs. improves" immediately legible without reading three
     paragraphs.
   Follow `dataviz`'s form heuristic for each (a headline number some of
   these deserve a stat tile, not a chart) and run the palette validator
   before finalizing.
5. **Keep it condensed.** The target reading time is under five minutes.
   If a section is growing past what an executive would actually read,
   cut prose and lean on the findings table and figures — the underlying
   `results/*.md` files are the place for full derivations; this report
   links to them (`href` to a repo path, or name the exact filename) — it
   does not restate them.
6. **Publish as a self-contained HTML artifact** (per `artifact-design`),
   with a `<title>`, an accurate `description`, and a stable favicon. If
   the audience needs a static file instead of a link (e.g. for an email
   attachment or a printed leave-behind), offer to also produce a PDF or
   DOCX version via the `pdf`/`docx` skills from the same findings
   ledger — but the HTML artifact is the default, since it's the only
   format that renders the figures as real, inspectable charts rather
   than flattened images.

## What this does NOT do

- It does **not** run any new experiment, dispatch any rating sub-agent,
  or generate any new data point — see the companion skills under
  "Related" for that. This skill only synthesizes what already exists.
- It does **not** round, estimate, or "reasonably infer" a number that
  isn't actually stated in a source file. If a figure is genuinely
  unavailable (e.g. a partial loss curve where only two epochs were
  recorded), say so in the figure's caption rather than interpolate
  invented points.
- It does **not** average away or soften a rejected finding to make the
  report read more positively — a rejected knob level, a diluting signal,
  and an `UNVALIDATED` calibration status get the same prominence as an
  adopted change. This report exists to inform a decision, not to make
  the research program look finished.
- It does **not** treat this report itself as a source of truth going
  forward — the underlying dated results files remain canonical; a
  future run of this skill regenerates the report from them, it never
  edits a results file to match something the report already said.

## Related

- [`model-right-sizer-layer-ablation`](../model-right-sizer-layer-ablation/SKILL.md),
  [`model-right-sizer-prompt-tuning`](../model-right-sizer-prompt-tuning/SKILL.md),
  [`model-right-sizer-holdout-tuning`](../model-right-sizer-holdout-tuning/SKILL.md),
  [`model-right-sizer-signal-validation`](../model-right-sizer-signal-validation/SKILL.md)
  — the four companion skills that can re-run a piece of this research;
  this skill's reproducibility appendix points to all four.
- [`../../eval/tuning/DESIGN.md`](../../eval/tuning/DESIGN.md) and
  [`../../eval/ablation/DESIGN.md`](../../eval/ablation/DESIGN.md) — the
  two narrative logs this report condenses.
