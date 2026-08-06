# Changelog

All notable changes to CloudZero (the CloudZero plugin marketplace) and its plugins will be documented in this file. Plugin-specific history may also live in a plugin's own changelog (e.g. [plugins/model-right-sizer/CHANGELOG.md](plugins/model-right-sizer/CHANGELOG.md)).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-04-10

### Added

#### Cost Projection Skills (2 New)

**Diff Cost Projection** (`/diff-cost-projection`)
- Analyzes code diffs (PRs, branches, workspace changes) for infrastructure cost impact
- 7-phase pipeline: retrieve diff, classify files, detect cost signals, map to CloudZero dimensions, query baselines, synthesize estimates, format report
- Detects Terraform, CDK, CloudFormation, SAM, K8s, scaling, and application code changes
- 4 cost impact classes: direct IaC, scaling, indirect app code, removals
- Confidence levels (HIGH/MEDIUM/LOW) with reasoning
- Early exit for non-impacting changes; optional PR comment posting

**Cost Projection** (`/cost-projection`)
- Projects monthly cost of infrastructure definitions before deployment
- Auto-discovers IaC files, CDK constructs, K8s manifests, and cloud SDK usage in codebases
- Enumerates resources, maps to CloudZero dimensions, queries actual spend for existing resources
- Looks up current AWS pricing via web search for new resources
- Line-item cost breakdown by service/resource with monthly totals
- Supports Terraform, CDK, CloudFormation, SAM, Serverless Framework, Pulumi

#### New Reference Documents
- `cost-impact-taxonomy.md` — detailed patterns for cost impact classification
- `service-mapping.md` — IaC resource types to CloudZero dimension mapping
- `cost-impact-output-examples.md` — sample diff cost projection report formats
- `cost-projection-output-examples.md` — sample cost projection report formats

---

## [1.0.0] - 2025-12-05

### Added

#### Core Plugin Infrastructure
- Initial release of CloudZero Cost Analyst Plugin for Claude Code
- Plugin name: `cost-analyst` in marketplace: `cloudzero` (install as `cost-analyst@cloudzero`)
- Plugin packaging with `.claude-plugin/plugin.json` manifest
- **Plugin marketplace support** with `.claude-plugin/marketplace.json` for simplified installation
- Dual installation support: as plugin or cloned repository
- Pre-configured CloudZero MCP server integration via `.mcp.json`
- Shared reference files at plugin root (`references/`) using `${CLAUDE_PLUGIN_ROOT}` paths
- Symlinked `.claude/skills/` to root `skills/` directory for dual-mode operation

#### Foundational Skill

**Understand CloudZero Organization** (NEW)
- Retrieves and caches organization-specific context
- Loads custom dimensions, workflows, and business context
- Required prerequisite for all other cost analysis skills
- Prevents redundant API calls by caching context per conversation

#### Cost Analysis Skills (8 Total)

1. **Cost Spike Investigation**
   - Identifies and explains sudden cost increases
   - Compares recent spending to baseline periods
   - Multi-dimensional root cause analysis
   - Actionable remediation recommendations

2. **Top Cost Drivers**
   - Ranks highest cost contributors across dimensions
   - Multi-dimensional breakdown capabilities
   - 80/20 analysis and concentration metrics
   - Optimization priority identification

3. **Cost Trend Analysis**
   - Time-series cost pattern analysis
   - Growth rate calculations (WoW, MoM, QoQ)
   - Trend forecasting and projection
   - Seasonal pattern detection

4. **Cost Comparison**
   - Period-over-period comparisons
   - Environment benchmarking (prod vs staging vs dev)
   - Team/account efficiency comparison
   - Normalized cost metrics

5. **Service Cost Deep Dive**
   - Detailed service-specific cost analysis
   - Multi-dimensional service breakdowns
   - Service-specific optimization recommendations
   - Usage pattern analysis

6. **Tag Coverage Analysis**
   - Tagging quality and coverage evaluation
   - Untagged resource identification
   - Tag value consistency checking
   - Governance improvement recommendations

7. **Custom Dimension Analysis**
   - Organization-specific dimension support
   - Business-aligned cost visibility
   - Showback/chargeback reporting
   - Hierarchical cost attribution

8. **Cost Anomaly Detection**
   - Statistical anomaly detection
   - Multi-dimensional anomaly scanning
   - Security and waste indicators
   - Prioritized anomaly reporting

#### Shared Reference Files

- **best-practices.md** (218 lines) - Universal cost analysis best practices
- **cloudzero-tools-reference.md** (460 lines) - Complete CloudZero MCP tool documentation and examples
- **cost-types-reference.md** (292 lines) - All cost types with quick selection guide
- **dimensions-reference.md** (267 lines) - Dimension types, FQDIDs, and discovery patterns
- **error-handling.md** (410 lines) - Common errors, troubleshooting, and solutions

#### Features

- **Plugin Marketplace**: Repository configured as Claude Code plugin marketplace for simplified installation
- **Dynamic Dimension Discovery**: All skills automatically discover and use organization-specific dimensions
- **CloudZero MCP Integration**: Full integration with CloudZero's Model Context Protocol server
- **Multi-Cloud Support**: Analysis capabilities for AWS, GCP, and Azure costs
- **Natural Language Interface**: Skills automatically invoked based on conversational requests
- **Comprehensive Documentation**: Detailed SKILL.md files with workflows, examples, and best practices
- **Organization Context Awareness**: Foundational skill loads context once, all other skills reference cached data
- **DRY Architecture**: 1,647 lines of shared content eliminates duplication across skills
- **Plugin-Portable References**: All references use `${CLAUDE_PLUGIN_ROOT}` for portability

#### Documentation

- Comprehensive README with installation instructions for both plugin and local use
- Detailed skill documentation including trigger keywords and examples
- Usage examples and common workflow patterns
- Tips for optimal results and best practices

### Technical Details

- Plugin structure follows Claude Code plugin specifications
- Skills organized in root `skills/` directory with symlink to `.claude/skills/`
- Each skill includes YAML frontmatter with name and description
- Skills designed for autonomous activation by Claude based on user intent
- All skills follow consistent workflow patterns and output formats
- Skills reference foundational **understand-cloudzero-organization** skill for context
- Skills reference shared content in `references/` directory using `${CLAUDE_PLUGIN_ROOT}` paths
- Skills reference each other by name only (not by path)

### Installation Methods

- **Plugin marketplace** (recommended): `/plugin marketplace add cloudzero/cloudzero-claude-marketplace` then `/plugin install cost-analyst@cloudzero`
- Direct git URL installation: `/plugin install git+https://github.com/cloudzero/cloudzero-claude-marketplace.git`
- Team automation via `settings.json` with `extraKnownMarketplaces`
- Local clone and run from repository root

### Best Practices Applied

- Skills structured following Anthropic's guidelines
- Eliminated duplicate content across skills (1,647 lines extracted to shared references)
- Foundational skill pattern for organization context loading
- Plugin-portable paths using `${CLAUDE_PLUGIN_ROOT}`
- Skills under or near 500-line recommended limit
- Clear separation between skill-specific and shared content

---

## [Unreleased]

### Added

#### Model Right Sizer: a machine-wide learning loop (plugin 0.1.0 → 0.2.0)

The `model-right-sizer` agent had no memory: every spawn reasoned from first
principles, so the cost of a wrong pick was thrown away instead of informing the
next one. Its Pass A already had the hook ("close the loop, if a calibration
history exists") — nothing created that history. Now:

- **`model-right-sizer-learned`** — an additive skill seeded into the user-level
  skill directory, so every session in every repo discovers it. Distilled
  learnings between two SkillOpt-protected regions, alongside an append-only
  `ledger.jsonl` of measured recommended-vs-actual evidence.
- **`model-right-sizer-calibrate`** — a third companion skill and the write half
  the read-only agent can't provide: `append` (usage report → schema-valid
  rows), `summary` (aggregate by task shape — what makes the loop useful on day
  one), `review` (diff and adopt a staged proposal, only on an explicit yes).
- **A closed row schema** that keeps a shared ledger safe to read from any repo:
  rows record a task *shape* (`stage_kind`, `loop_class`, the three signals,
  recommended-vs-actual, rework cycles), never repo names, paths, ticket ids,
  code, or customer data — enforced structurally, not by good intentions.
- **Optional [SkillOpt-Sleep](https://github.com/microsoft/skillopt) wiring** to
  distill the ledger nightly behind a held-out gate, with a 16-task eval set
  covering the rubric's real decision boundaries. Optional is load-bearing: the
  plugin's "Prerequisites: None" still holds, and nothing is ever auto-adopted.

Every write outside the target repo requires explicit confirmation, and a
re-install never touches accumulated learnings. See
[plugins/model-right-sizer/CHANGELOG.md](plugins/model-right-sizer/CHANGELOG.md)
for the full entry.

### Planned

- Additional specialized skills for Reserved Instance analysis
- Savings Plan optimization skill
- Budget tracking and alerting integration
- Cost allocation rule recommendations
- Interactive cost report generation
- Integration with additional CloudZero features

---

## [1.2.0] - 2026-07-29

### Added

**Documentation catch-up: Optimize Triage skill** — the `optimize-triage` skill shipped in cost-analyst (bumping that plugin to 1.2.0) without README or changelog entries; now documented. It fetches top unaddressed CloudZero Optimize recommendations, dispatches parallel research agents with an SRE critique pass, and surfaces actionable findings. Research-only, but it is the only skill granted `Bash` (for read-only cloud CLI commands) — run it with read-only credentials.

**Model Right Sizer Plugin**
- Added the `model-right-sizer` plugin at `plugins/model-right-sizer/` (install as `model-right-sizer@cloudzero`), moved in from the standalone `Cloudzero/cloudzero-model-right-sizer` repository, which this marketplace now supersedes as its sole home
- Ships the `model-right-sizer` agent (a read-only model-selection economist that recommends the smallest Claude model, effort, and token budget that clears the bar for each task) plus two companion skills: `model-right-sizer-install` and `model-right-sizer-dryrun`
- Bumped marketplace `metadata.version` to 1.2.0 (1.1.0 was already used by the cost projection skills release)

**CI Validation**
- Added `.github/workflows/ci.yml` running on every push/PR to `main` — the repository previously had no CI
- Added `scripts/validate_plugin_manifest.py`: the marketplace catalog and every listed plugin manifest parse as JSON, carry the full documented metadata contract (name, description, version, author, homepage, repository, license, keywords), `source` paths resolve, and versions agree where declared on both sides
- Added `scripts/validate_agent_file.py`: real YAML frontmatter validation (a parse failure means Claude Code silently loads the agent with empty metadata), org-agnostic tool lists, and secret tripwires for every `plugins/*/agents/*.md`
- Added `scripts/validate_skill_frontmatter.py`: every `plugins/*/skills/*/SKILL.md` carries the frontmatter CONTRIBUTING requires and its `name` matches its directory
- Added pytest suites for all validators under `tests/`

**Repository Infrastructure**
- Added `.github/workflows/mirror-to-internal.yml` — mirrors this public marketplace into the private internal repository used by claude.ai organization plugin sync
- Added `CLAUDE.md` (PR-monitoring mandate and validation commands) and SECURITY.md scope notes covering the install skill's supply-chain behavior and per-skill tool grants

### Changed

**Repository Structure Refactoring**
- Restructured repository to support multiple plugins
- Created `plugins/` directory as the container for all plugins
- Moved cost-analyst plugin to `plugins/cost-analyst/` directory
- Moved marketplace configuration to root `.claude-plugin/marketplace.json`
- Updated marketplace.json to reference `plugins/cost-analyst/` as the plugin source
- Updated README to reflect new multi-plugin marketplace structure
- Each plugin is now self-contained with its own configuration, skills, and dependencies

**Branding**
- Renamed the marketplace's human-facing name to simply "CloudZero" with the tagline "AI-powered cloud and AI optimization" (machine name and install identifiers unchanged)

**Security Hardening (from pre-release security review)**
- Pinned CI Python dependency versions; Python tooling runs through `uv`
- Fixed the model-right-sizer agent's pricing-fetch URLs to the working `/docs/en/about-claude/` endpoints (old paths had started returning 404)
- Mirror workflow now pins GitHub SSH host keys from the TLS-authenticated meta API instead of trust-on-first-use `ssh-keyscan`
- `model-right-sizer-install` requires explicit user confirmation before running plugin-install commands or stamping the mandate when the agent is undiscoverable

---

## [1.0.1] - 2026-02-02

### Changed

**MCP Tool Naming Updates**
- Updated all references to renamed CloudZero MCP server tools:
  - `get_reference_information` → `get_reference_info`
  - `get_organization_context` → `get_org_context`
  - `get_optimize_recommendations` → `get_optimize_recs`
  - `set_organization_context` → `set_org_context`
  - `get_organization_context_versions` → `get_org_context_versions`
- Updated 5 documentation files with new tool names:
  - `plugins/cost-analyst/references/cloudzero-tools-reference.md`
  - `plugins/cost-analyst/skills/understand-cloudzero-organization/SKILL.md`
  - `plugins/cost-analyst/references/error-handling.md`
  - `plugins/cost-analyst/references/dimensions-reference.md`
  - `plugins/cost-analyst/references/best-practices.md`
- Total of 13 references updated across documentation

---

[Unreleased]: https://github.com/cloudzero/cloudzero-claude-marketplace/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/cloudzero/cloudzero-claude-marketplace/compare/v1.0.0...v1.2.0
[1.0.1]: https://github.com/cloudzero/cloudzero-claude-marketplace/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/cloudzero/cloudzero-claude-marketplace/releases/tag/v1.0.0
