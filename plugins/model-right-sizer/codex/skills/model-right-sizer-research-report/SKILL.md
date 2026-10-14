---
name: model-right-sizer-research-report
description: Publish an executive HTML report from recorded right-sizing experiments, including rejected/null findings; run no new experiments.
author: CloudZero, Inc.
version: 0.2.0
license: Apache-2.0
---

# Research report in Codex

Run this workflow in the main Codex agent. Read
`../model-right-sizer/SKILL.md` for the economic rules and resource locations,
then the **Research report** section of
`../model-right-sizer/references/workflows.md` for this workflow's full contract.
The entry point is native; it does not dispatch a separately installed
Model Right Sizer persona. Keep the explicit output shape, action scope,
independence requirements, and evidence discipline in that contract.

Use the bundled deterministic helpers directly. Report missing host controls
or observations; never label a fallback complete feature parity. Reuse the
user's existing authorization and experiment scope where applicable.
