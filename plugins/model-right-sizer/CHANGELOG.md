# Changelog

All notable changes to `model-right-sizer.md` are documented here, most recent first. This project doesn't cut version tags — entries are dated. Loosely follows [Keep a Changelog](https://keepachangelog.com/) conventions (Added / Changed / Fixed).

## Unreleased

### Changed
- **Moved into the CloudZero Plugin Marketplace** — this plugin now lives at
  `plugins/model-right-sizer/` in
  [cloudzero/cloudzero-claude-marketplace](https://github.com/cloudzero/cloudzero-claude-marketplace),
  which is its sole home going forward (the standalone
  `Cloudzero/cloudzero-model-right-sizer` repo is superseded). The install
  flow changed accordingly:
  `/plugin marketplace add cloudzero/cloudzero-claude-marketplace` followed by
  `/plugin install model-right-sizer@cloudzero`. The plugin's own
  `marketplace.json` was dropped (the marketplace catalog at the repo root
  registers it now), all `repository`/`homepage` URLs and the
  `model-right-sizer-install` skill's install commands and fallback links
  were repointed, and the CI validators moved to the marketplace repo's
  `scripts/` where they now validate every plugin in the catalog.

### Added
- `scripts/validate_plugin_manifest.py` (wired into CI's `validate` job, plus
  `tests/test_validate_plugin_manifest.py`) — checks that
  `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` both
  parse as valid JSON, carry their required fields, that each marketplace
  entry's `source` resolves to a real plugin directory whose own `name`
  matches, and that the two manifests' `version` fields agree. Before this,
  CI only validated `agents/model-right-sizer.md` — a broken manifest (bad
  JSON, a stale `source` path, a version that drifted between the two
  files) would have shipped silently and only surfaced as an install-time
  failure for a consumer.

### Changed
- `model-right-sizer-install` step 2 now **actively installs** the
  `model-right-sizer` Claude Code plugin (`/plugin marketplace add` +
  `/plugin install`) when the agent isn't already discoverable in the target
  repo, instead of only telling the user how to add it themselves. Falls
  back to the previous manual copy/submodule instructions if plugin install
  isn't available in the runtime. Updated the frontmatter `description`,
  the skill's own scope framing, and the root README's "What's in this
  repo" and "Action scope" sections to match this widened (but still
  narrowly-scoped-to-its-own-dependency) blast radius; added a
  corresponding note to `SECURITY.md`'s supply-chain bullet.
- Restructured this repo into a proper installable **Claude Code plugin**:
  added `.claude-plugin/plugin.json` (the plugin manifest) and
  `.claude-plugin/marketplace.json` (so the repo self-hosts its own
  marketplace catalog and can be added with
  `/plugin marketplace add Cloudzero/cloudzero-model-right-sizer` followed by
  `/plugin install model-right-sizer@cloudzero-model-right-sizer`, with no
  separate marketplace repo required). Moved `model-right-sizer.md` to
  `agents/model-right-sizer.md` — the plugin convention's default
  auto-discovered agent directory — instead of the repo root. Motivated by
  making the agent and its companion skills installable as a single unit
  through Claude Code's plugin system, rather than requiring a manual
  copy-the-file drop-in for every consumer.
- Renamed the `model-right-sizer-init` skill to **`model-right-sizer-install`**
  (directory `skills/model-right-sizer-init/` → `skills/model-right-sizer-install/`,
  frontmatter `name` field, the mandate-block marker comment, and all
  cross-references in this skill, `model-right-sizer-dryrun`, and the root
  README/CLAUDE.md) — "install" more accurately names what the skill does
  (stamp a mandate into a target repo) now that this repo is a real
  installable plugin, and avoids confusion with Claude Code's own `/init`
  command. No behavior change: same idempotent, append-only mandate-stamping
  logic.
  **Migration note:** a repo onboarded before this rename has a stamped
  `CLAUDE.md` mandate block whose closing line says to re-run the
  `model-right-sizer-init` skill to refresh it — that skill name no longer
  exists in this plugin. If you hit that, just invoke
  `model-right-sizer-install` instead; running it once rewrites the block
  (including that closing line) to the current name, so this is a one-time
  fix-up per already-onboarded repo, not a recurring issue.
- Corrected several stale/inconsistent `repository` URLs across
  `agents/model-right-sizer.md`, both `SKILL.md` files, the README badge, and
  `.github/ISSUE_TEMPLATE/config.yml` (previously a mix of
  `Cloudzero/project-model-right-sizer` and `djo-cz/model-right-sizer`) to
  the actual repo, `Cloudzero/cloudzero-model-right-sizer`.
- The model lineup is now retrieved at spawn instead of hand-maintained: the agent delegates the pricing/model-overview fetch to the cheapest capable tier (a `Task` dispatch to a Haiku-class model, or the smallest tier your framework exposes), caches it for the run, and only falls back to the in-file table — now explicitly marked "illustrative snapshot, last-resort fallback only, do not hand-edit" — if delegation and direct `WebFetch` both fail. Motivated by the Opus 5 addition above: adding a new release by hand-editing this file every time a model ships doesn't scale, so retrieval replaces maintenance as the primary path. Added `Task` to the frontmatter `tools` field for the delegated fetch; added a new "bounce from" condition for hand-editing the table instead of delegating.
- Relicensed from MIT to Apache License 2.0 (`LICENSE`, `NOTICE` added) to
  comply with CloudZero's `govern-opensource-ai` standard, which mandates
  ALv2 for all CloudZero open-source releases. Added `license`, `author`,
  and `repository` frontmatter fields to `model-right-sizer.md` and both
  `SKILL.md` files; added inbound-licensing terms to `CONTRIBUTING.md`;
  added a License + Trademarks section pair and AI-specific README sections
  (prerequisites, configuration, supported models, action scope, example
  interactions, limitations) required for AI-project OSS releases.
- A `.pre-commit-config.yaml` (`gitleaks`) is available for local use.
  `.gitignore` now excludes `.env*` (never applicable to this repo's own
  code, but required by the standard for any consumer copying this repo's
  structure). Secret scanning in CI is handled by GitHub Advanced Security.

### Fixed
- Removed the `secrets` CI job (which used `gitleaks-action`, requiring a paid
  org secret) — secret scanning and push protection are handled by GitHub
  Advanced Security, already enabled on this repo. Removed `secrets` from
  branch protection required checks accordingly.
- `CONTRIBUTING.md` and `.github/PULL_REQUEST_TEMPLATE.md` now list all seven
  required frontmatter fields (`name`, `description`, `tools`, `model`,
  `license`, `author`, `repository`) instead of only the original four.
- `SECURITY.md` now correctly attributes maintenance to CloudZero, Inc. and
  its open-source maintainers rather than describing a personal project.
- Added `.pytest_cache/` to `.gitignore`.
- Removed unused `import textwrap` from `tests/test_validate_agent_file.py`.
- `scripts/validate_agent_file.py` now enforces the `license`, `author`, and
  `repository` frontmatter fields introduced in this PR; previously they were
  present in the files but absent from `REQUIRED_FIELDS`, so CI would pass
  even if a contributor removed them. Added `tests/test_validate_agent_file.py`
  to prevent regression.

### Added
- Claude Opus 5 (`claude-opus-5`, $5/$25, 1M context, 128K max out) as a new flagship row in the model lineup, above Opus 4.8. Deliberately *not* made the live default: it sits at exact price parity with the proven Opus 4.8, so the row frames promotion over 4.8 as `measurement-required` — realized reliability, not token cost, is the only open question — keeping 4.8 as the live default until a real run clears the bar. This applies the agent's own cost-of-error / don't-marry-the-newest-model stance to a brand-new top-tier model. Pricing/specs anchored to platform.claude.com, not the system card (system cards carry no pricing).
- `skills/model-right-sizer-dryrun` — a companion skill that turns a free-text intent into the agent's Pass A (blueprint) routing map on demand, then stops: no build, no file edits, no Pass B usage report. It unbundles the front bookend as a "what would this cost / how would this route" preview, without inventing a new agent mode (a dry run is simply Pass A run against a hypothetical).
- Deterministic-query-layer guidance: the blueprint now flags data-query-shaped stages (lookups, joins, aggregation, arithmetic over the task's own data) that a semantic/deterministic query layer (e.g. PromptQL) would answer more reliably and cheaper than a raw model call. Framed as a routing fork ("model tier vs. query layer"), not just another tier.
- Agent-to-agent message-schema design as a first-class lever: a new "Agent-to-agent message-schema design" section, a `handoff schema` column in the blueprint table and work-routing map, and a dedicated blueprint deliverable specifying the structured payload (and exclusion list) each stage hands its consumer.
- Schema adherence as a Pass B (usage report) grading line, alongside the existing budget-adherence line.
- Two new model-selection principles, two new "bounce from" conditions, and new vocabulary terms (`deterministic query layer`, `query-plan reuse`, `message schema`, `handoff payload`, `schema adherence`) covering both additions above.

## 2026-07-21

### Added
- Agentic-loop latency economics: loop-class scoring and a measurement-gated down-pin rule for agentic (≥3 tool-turn) calls, so a smaller model isn't pinned live on token-cost projection alone.
- `skills/model-right-sizer-init` — a companion skill that stamps a narrow, organization-agnostic mandate onto a target repo's `CLAUDE.md`.
- Open-source hardening: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, CI validation script (`scripts/validate_agent_file.py`), issue templates.

### Initial release
- `model-right-sizer.md` — the agent core: effectiveness/efficiency/difficulty scoring, the model lineup table, adaptive reasoning-budget layers (IBPO, BudgetThinker), the blueprint (Pass A) and usage-report (Pass B) output shapes, voice/biases, and model-selection principles.
