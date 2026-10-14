---
name: model-right-sizer-holdout-tuning
description: Tune native right-sizing wording against measured Codex actuals using three independent blind draws per candidate.
author: CloudZero, Inc.
version: 0.2.0
license: Apache-2.0
---

# Holdout tuning in Codex

Run this workflow in the main Codex agent. Read
`../model-right-sizer/SKILL.md` for the economic rules and resource locations,
then the **Holdout tuning** section of
`../model-right-sizer/references/workflows.md` for this workflow's full contract.
The entry point is native; it does not dispatch a separately installed
Model Right Sizer persona. Keep the explicit output shape, action scope,
independence requirements, and evidence discipline in that contract.

Use the bundled deterministic helpers directly. Report missing host controls
or observations; never label a fallback complete feature parity. Reuse the
user's existing authorization and experiment scope where applicable.
