---
name: model-right-sizer-learned
description: >-
  Accumulated, repo-agnostic right-sizing calibration for the
  `model-right-sizer` agent — which of its past picks held, which cost rework,
  and which were oversized. Read it during Pass A (the right-sizing blueprint)
  before finalizing any model/effort/budget pick, and grade against it in
  Pass B (the usage report). Evidence is appended by
  `model-right-sizer-calibrate`; the prose below is distilled from that
  evidence by SkillOpt-Sleep behind a held-out validation gate. Applies in
  every repo — it records task SHAPES, never task content.
author: CloudZero, Inc.
version: 0.1.0
license: Apache-2.0
---

<!-- SLOW_UPDATE_START -->
## Contract — protected region, do not edit by training

This skill is the **memory** the `model-right-sizer` agent otherwise lacks. It
augments, and never replaces, `agents/model-right-sizer.md`: the agent file
holds the rubric reasoned from first principles, this file holds what actually
happened when that rubric met real work.

- **Where it plugs in.** Pass A, step 8 ("close the loop") reads this file plus
  `ledger.jsonl` before finalizing picks. Pass B emits a calibration row that
  `model-right-sizer-calibrate` appends to that ledger.
- **Two artifacts, two jobs.** `ledger.jsonl` is append-only *evidence* — one
  schema-validated row per measured stage. The "Calibration learnings" section
  below is *distilled state* — prose that only changes when a proposed edit
  clears a held-out validation gate.
- **Repo-agnostic, always.** Rows and learnings describe task shapes
  (`code-review`, `agentic`, `structured-extraction`), never repo names, file
  paths, ticket ids, code, or customer data. This file is read in every repo on
  the machine; anything repo-specific in it is both a leak and a wrong signal.
- **A measured row outranks a seed prior.** Learnings tagged
  `provenance: seed` are unvalidated first-principles starting points. The
  first real measurement that contradicts one displaces it — do not defend a
  seed against evidence.
- **How to change it.** Add evidence with `model-right-sizer-calibrate append`.
  Review and apply distilled edits with `model-right-sizer-calibrate review`
  (which wraps `skillopt-sleep status` / `adopt`). Hand-editing the trainable
  body is allowed but unaudited — prefer the loop.
- **Never let it override a fresh price sheet.** A learning about *relative*
  fit survives a model release; a learning that quotes a *price* does not.
<!-- SLOW_UPDATE_END -->

## Calibration learnings

Distilled, gate-validated right-sizing lessons. Each carries a provenance tag
and the row ids behind it. Cite the ids that move a pick.

- **L-001** · `provenance: seed (unvalidated)` · Agentic stages (≥3 tool turns)
  that were down-pinned on token-cost projection alone tend to converge in more
  turns, eroding or inverting the saving. Hold an agentic down-pin at
  `measurement-required` until a wall-clock sample lands within 1.15× the
  ambient default.
- **L-002** · `provenance: seed (unvalidated)` · Stages whose real job is a
  lookup, join, or aggregation over structured data are mis-framed as a model
  tier choice. Check the deterministic-query-layer fork before assigning any
  tier.
- **L-003** · `provenance: seed (unvalidated)` · High effort on a low-difficulty
  stage is the over-thinking tax and shows up as `adherence.budget: under` with
  `outcome.quality: held` — that pairing is evidence the tier or the effort was
  oversized, not that the pick was good.
- **L-004** · `provenance: seed (unvalidated)` · `outcome.quality: rework` with
  `rework_cycles ≥ 2` on a down-pinned stage is the cost-of-error signal. Two
  such rows for one `stage_kind` justify sizing that shape back up.
- **L-005** · `provenance: seed (unvalidated)` · A stage with no stated budget
  and no defined handoff schema is under-specified regardless of how well its
  tier was chosen; record it as `not-designed` rather than silently passing it.

<!-- APPENDIX_START -->
## Execution reminders — protected region, do not edit by training

- State the ledger's size out loud in Pass A: "no ledger yet" or "N rows,
  M relevant to this stage_kind". Silence about the evidence base is the
  failure mode this file exists to fix.
- Cite the learning ids (`L-00x`) and row ids (`cal-000x`) that changed a pick,
  and say explicitly when the ledger changed *nothing*.
- Distinguish a seed prior from a measured learning when you cite it. A seed
  prior is the agent's own rubric restated — it is not independent evidence,
  and leaning on it as if it were is double-counting.
- Never treat a confidence % here as a measured statistic. It is a calibrated
  judgment, exactly as in the agent file.
<!-- APPENDIX_END -->
