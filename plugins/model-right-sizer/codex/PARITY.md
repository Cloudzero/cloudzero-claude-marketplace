# Codex feature parity evidence

This implementation preserves the baseline feature inventory and provides native
main-agent workflows. **Absolute 1:1 parity is not yet certified.** Passing
deterministic tests cannot replace live execution, calibration, or surface tests.

| Feature | Implemented | Verification / remaining evidence |
|---|---|---|
| Main-agent integration and installation | Native main skill; eleven companion entry points; portable installer | Real Codex app-server discovered all twelve enabled skills without errors. Idempotence, standalone resources, collisions and local-edit protection tested. |
| Economic rubric, pricing freshness, effort, query/caching/batch/serving levers | Native main workflow; shared research and formulas | Shared formula/citation tests pass; live available-model discovery verified. Fresh prices and model-routing effectiveness remain unmeasured. |
| Blueprint / dry run | Complete shared schema; native semantic checks; dry run has no execution | Schema and negative cases tested. Main-session dogfood emitted a validated live blueprint. The original attempt was blocked by authentication; a later fresh CLI completion succeeded. |
| Usage report | Deterministic accounting plus main-agent synthesis | Main-session real-task reconciliation exercised; missing counts remain unknown. Live CLI and app-server token telemetry now verified; actual model shares are scoped to recorded experiments. |
| Budget guard / status ledger | Fresh timestamps, valid transitions, configurable threshold, pending versus delivered warning | Real main-task transitions dogfooded; boundary/delivery/unknown cases tested with labeled fixtures. Three matched live guard pairs and one persisted-thread probe delivered acknowledged warnings, preserved required quality, and finished under budget. Billing polls returned no usage; native notifications drove correction. |
| Repository audit | Native call-site discovery, independent evaluation, reviewed blueprint/PR contract | Independent live evaluation and remote PR lifecycle need authenticated execution. No application settings are changed by the workflow. |
| Handoff schema | Native design/stamp workflow; portable shared full validator | Existing family/stamp fidelity regressions pass; installed validator exercised standalone. Native agent-generated prescription/stamp still needs live evaluation. |
| Layer ablation | Native renderer with all sixteen conditions, shared benchmarks/metrics | All conditions render; independent six-task layer sweeps remain unmeasured. |
| Prompt tuning | Six native wording knobs with shared finite domains and optimizer | Every knob level renders. Real-build coordinate-ascent and held-out outcomes remain unmeasured. |
| Holdout tuning | Three-draw blind native workflow | Three isolated native draws with zero tool calls collected; prompt-holdout optimization itself remains unmeasured. |
| Signal validation | Native six-signal nonnegative fit, measured floors, three blind draws, task-held-out promotion gates | Shipped measured medium-effort profiles for GPT-6.1-Sol and GPT-6-Astra: 12 development shapes, 4 fresh held-outs and 3 floor probes per model. Luna failed coverage and remains a candidate. See results/2026-10-01-live-calibration.json. |
| Research report | Native synthesis-only HTML/chart workflow | Historical evidence stays labeled by runtime; a native model-generated executive report has not been validated. |
| Release report / historical backfill | Native version-specific synthesis workflow | Historical report logic remains shared; new native release/backfill output still needs live verification. |
| CloudZero spend attribution | Local structured export; explicitly sourced realized spend | Record shape and privacy exclusions tested. Live CloudZero connection/ingestion is not implemented. |

The original dogfood attempt used Codex CLI 0.159.0-alpha.3. Model discovery and skill
discovery worked. A fresh `codex exec` turn failed because the cached access
token could not refresh. The authenticated main session then completed a real
CSV allocation CLI and seven correctness/exit-code tests using the installed
workflow. It exposes no per-unit usage signal, so spend, warnings based on real
spend, and native calibration remain unknown rather than fabricated.

Subsequent device authentication succeeded. Live calibration and guard evidence is
recorded separately; the original missing-usage evidence remains unchanged.

CLI/IDE repository-skill packaging is implemented. Desktop/cloud/UI publication,
host-specific model controls, lifecycle callbacks, and all surface combinations
require separate end-to-end verification. AGENTS.md is a standing instruction,
not a guaranteed host hook. No separately installed economist agent is needed.
