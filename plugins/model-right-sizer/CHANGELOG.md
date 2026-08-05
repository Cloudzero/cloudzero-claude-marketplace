# Changelog

All notable changes to `model-right-sizer.md` are documented here, most recent first. This project doesn't cut version tags — entries are dated. Loosely follows [Keep a Changelog](https://keepachangelog.com/) conventions (Added / Changed / Fixed).

## Unreleased

### Added
- **A machine-wide learning loop — the agent now has a memory across sessions
  and repos.** Pass A step 8 has always said "close the loop, if a calibration
  history exists," but nothing created that history: every spawn reasoned from
  first principles, and the README listed "no memory across spawns" as a
  limitation. The loop that fills it:
  - **`model-right-sizer-learned`** — an additive skill seeded into the
    user-level skill directory (`~/.claude/skills/model-right-sizer-learned/`),
    so *every* session in *every* repo discovers it. Carries distilled
    learnings between two protected regions
    (`<!-- SLOW_UPDATE_START/END -->`, `<!-- APPENDIX_START/END -->`) that hold
    the contract and execution reminders, alongside an append-only
    `ledger.jsonl` of measured evidence. Shipped as
    `templates/learned-skill.seed.md` — deliberately *outside* `skills/`, since
    a seed under `skills/` would be discovered as a second, never-learning copy
    of the installed skill.
  - **`skills/model-right-sizer-calibrate/`** — the write half the read-only
    agent can't provide. `append` turns a Pass B usage report into
    schema-valid rows; `summary` aggregates the ledger by task shape (what Pass
    A reads on day one, before any distillation has run); `review` diffs a
    staged SkillOpt proposal and adopts it only on an explicit yes.
  - **`templates/ledger-entry.schema.json`** — the authoritative row schema,
    and the mechanism that makes machine-wide storage *safe*. A row records a
    task **shape**, never task content: `additionalProperties: false` at every
    level, a closed `stage_kind` vocabulary, and a 240-char cap on the single
    free-text field. Repo-agnosticism here isn't a nicety — it's the
    precondition for storing the evidence centrally at all, which in turn is
    what lets cost-of-error reach a sample size that means anything.
  - **`eval/routing-tasks.jsonl`** — 16 synthetic, repo-agnostic routing
    decisions covering the rubric's real boundaries (agentic down-pin, the
    deterministic-query-layer fork, the over-thinking tax, cost-of-error
    size-up, caching/batch economics, handoff seams, no-false-certainty), as
    the held-out gate a distilled learning must clear.
  - **Optional [SkillOpt-Sleep](https://github.com/microsoft/skillopt)
    integration** (`templates/skillopt-sleep.config.json`) to distill the
    ledger nightly behind that gate. Deliberately optional — the plugin's
    "Prerequisites: None" still holds, because the ledger, the summary, and the
    agent reading both work with nothing installed. Sleep stages proposals; it
    never auto-adopts, and the install skill surfaces the transcript-harvesting
    privacy note before anyone agrees to a nightly job.
  - **`skills/model-right-sizer-eval/`** — the audit harness that answers
    "does the loop actually work," built to be able to return *no*. Three
    rounds × two arms over **disjoint** task sets, so a gain is transfer rather
    than recall; a **no-memory control arm every round**, so set difficulty
    can't masquerade as improvement; and **sandbox isolation** keeping the agent
    out of this repo, whose own `eval/routing-tasks.jsonl` spells the answers
    out in its `reference_text`. Plus `eval/boundary-rubric.json` (the eight
    boundaries and their 3-point scoring) and `eval/probe-set-A.jsonl` (the
    first set, kept as a worked example and marked **burned** — publishing it
    contaminated it).
  - **A Stage 0 "wire test" in that harness** — whether memory improves accuracy
    is unanswerable until you know it is read at all. Plants a sentinel learning
    that contradicts first principles, carries a per-run nonsense codename, and
    ships with matching ledger rows; runs the agent blind alongside a no-memory
    control; and runs **twice** — once with rows that support the sentinel's
    claim, once with rows that contradict it. Four pass criteria: read · scoped ·
    responsive · **resistant**. The last is the one that matters most: an agent
    that obeys any text in its memory file is suggestible rather than
    calibrated, and one bad distillation would poison every later pick.

    **Result 2026-08-05, all four passed.** Control picked Haiku 4.5 @ `none`
    (conf 0.68). The malformed sentinel was **rejected** — the agent noticed its
    rows recorded the *top* tier reworking, so a claim about the cheapest tier
    rested on a model with zero measured runs in its own evidence, and it
    flagged the synthetic numeric signature besides. The valid sentinel was
    **followed**: pick moved to Sonnet 5 @ `low` (conf 0.62), with the agent
    volunteering the counterfactual ("without the ledger I would have picked
    Haiku 4.5 @ none, ~$32, confidence ~0.75") that the control run
    independently confirms. Rows were cited individually — two of seven
    discounted as possibly mitigated by the task's conditions, which is why
    confidence landed at 0.62 rather than higher. A second task with no matching
    `stage_kind` was reported unmatched with its pick untouched, in every arm.

    Same agent, same task, same sentinel id; the only variable was whether the
    rows supported their claim. The loop is **live and discriminating** — it
    responds to evidence quality, not to the presence of text in a file. It does
    **not** yet show that accumulation over rounds raises accuracy.
  - **A `saturation_gate` in that harness, added because its own first run
    failed it.** Run 2026-08-05, Set A, both arms on Opus: control **24/24**,
    treatment **24/24**. Rounds 2 and 3 were not run — continuing would have
    cost ~200k tokens to confirm a ceiling already reached, and any reported
    trend would have been noise. The result does not show the loop works; it
    shows the eval couldn't tell, because every boundary tested is one the agent
    file teaches explicitly. The rule it produced is now the harness's spine:
    *a calibration ledger can only pay for itself on questions first principles
    cannot settle* — so discriminating sets test environment-specific
    economics, genuinely contested calls, local threshold calibration, and
    anti-learning (a stale learning must lose to a fresh price sheet).
  - **`tests/test_learned_skill_seed.py`** — the loop's artifacts live outside
    `plugins/*/skills/*/SKILL.md`, so no existing validator sees them. Pins the
    seed's frontmatter `name` to its install directory (a drift there silently
    breaks every cross-reference), checks the protected regions are present,
    balanced, and bracketing the trainable section, and asserts the schema
    stays closed. Also covers the audit harness: the rubric keeps all three
    scoring criteria and its saturation gate, a probe set exercises every scored
    boundary exactly once, and a shipped probe set stays marked burned and
    carries **no** answer fields — so a leaked set alone gives an agent nothing.

### Changed
- `agents/model-right-sizer.md` — Pass A step 8 now names the discovery
  convention (the learned skill + ledger, and the task-shape contract) instead
  of an abstract "if a ledger exists"; Pass B emits calibration rows for the
  session to persist, with an explicit "omit what you didn't measure, never
  estimate into the ledger" rule — an invented token count is indistinguishable
  from a measurement afterward and poisons every future pick that reads it. The
  agent stays **read-only**: it emits rows, it never writes them. The
  "Extending this agent" section now draws the line between the two overlay
  kinds: rubric reasoned from first principles stays in the agent file,
  anything true only *because of past runs* belongs in the learned skill.
- `model-right-sizer-install` (0.1.0 → 0.2.0) — seeds the learned skill (never
  clobbering accumulated learnings on re-run; only the protected regions
  refresh), stamps a `model-right-sizer-learning-loop` block into the
  user-level `CLAUDE.md`, extends the repo mandate to honor the loop, and
  offers to wire SkillOpt-Sleep. Every write outside the target repo requires
  explicit confirmation first — the same bar the skill already applied to
  plugin installs — and the closing report says per artifact what was created,
  refreshed, skipped, or declined, including what a declined write costs.
- `model-right-sizer-dryrun` — reads the ledger as part of Pass A, and is
  explicit that a dry run never appends to it (nothing ran, so there's nothing
  to measure).

### Changed
- **Moved into CloudZero (the CloudZero plugin marketplace)** — this plugin now lives at
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
- Security-review hardening during the move: the install skill now asks for
  explicit user confirmation before running the plugin-install commands and
  before stamping the mandate when the agent is undiscoverable, and the
  agent's pricing-fetch URLs were fixed to the working
  `platform.claude.com/docs/en/about-claude/...` endpoints (the old paths
  had started returning 404, silently forcing every run onto the stale
  in-file snapshot).

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
