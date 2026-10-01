---
name: model-right-sizer-audit
description: Audit real model call sites in a repository and assemble a validated right-sizing blueprint; optionally open a reviewed PR.
author: CloudZero, Inc.
version: 0.2.0
license: Apache-2.0
---

# Audit in Codex

Run this workflow in the main Codex agent. Read
`../model-right-sizer/SKILL.md` for the economic rules and resource locations,
then the **Audit** section of
`../model-right-sizer/references/workflows.md` for this workflow's full contract.
The entry point is native; it does not dispatch a separately installed
Model Right Sizer persona. Keep the explicit output shape, action scope,
independence requirements, and evidence discipline in that contract.

Use the bundled deterministic helpers directly. Report missing host controls
or observations; never label a fallback complete feature parity. Reuse the
user's existing authorization and experiment scope where applicable.
