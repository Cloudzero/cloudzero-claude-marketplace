---
name: release
description: >-
  Cut a release of this repository (the CloudZero plugin marketplace itself
  — not a customer-facing plugin). Promotes every touched plugin's own
  `Unreleased` changelog section to a dated entry, synthesizes those changes
  into a new SemVer section at the top of the root `CHANGELOG.md`, bumps
  `.claude-plugin/marketplace.json`'s version, runs the full CI validation
  suite locally, tags the release, publishes a GitHub Release, and opens
  the companion docs PR against `Cloudzero/cloudzero-documentation`'s
  `v2.0` branch so customer-facing docs land in step with the code. This is
  a maintainer-only, repo-local skill (lives in `.claude/skills/`, not
  inside a `plugins/*/skills/` directory) — it is never installed by
  marketplace consumers. Use when told "cut a release", "release the
  marketplace", "ship a new version", "promote the changelog", or after
  merging PR(s) that need a version bump and a docs update — mirroring how
  v1.2.0 (the Model Right Sizer launch) shipped.
author: CloudZero, Inc.
version: 1.0.0
license: Apache-2.0
---

# release — cut a marketplace release

This skill packages the release process this repo has run by hand twice
(v1.0.0, v1.2.0) into a repeatable set of steps, so cutting a release
doesn't depend on one person remembering the mechanics. It is intentionally
**maintainer tooling for this repo**, not a plugin: it lives in
`.claude/skills/` at the repo root, discovered automatically when a Claude
Code session opens here, and is out of scope for
`scripts/validate_skill_frontmatter.py` (which only scans
`plugins/*/skills/*/SKILL.md`) and for the marketplace catalog — customers
installing `cloudzero` never see it. Don't move it into a plugin to "make
it official"; that would ship internal release tooling to every customer
for no reason.

## Before you start

**Confirm every PR meant for this release is already merged to `main`,
CI-green, with every review thread resolved** (the standing PR-ownership
rule in this repo's `CLAUDE.md`). This skill promotes and ships what's
already on `main` — it does not merge PRs for you.

## What to do

1. **Scope the release.** Find the last tag (`git describe --tags
   --abbrev=0`) and diff it against `main` (`git log <last-tag>..main
   --oneline`) to see every commit going into this release. Cross-check
   against the root `CHANGELOG.md`'s `## [Unreleased]` section and every
   `plugins/*/CHANGELOG.md` that has its own `## Unreleased` (or, for a
   plugin whose changelog uses dated headers instead of SemVer — check its
   own intro line, e.g. model-right-sizer's "this project doesn't cut
   version tags" — its topmost dated section if it's newer than the last
   marketplace tag). A commit with no changelog trace anywhere is a gap:
   surface it rather than silently shipping undocumented behavior.

2. **Decide the version bump and confirm it.** Apply SemVer against the
   root marketplace version in `.claude-plugin/marketplace.json`
   (`metadata.version`): MAJOR for a breaking change to an installed
   plugin's contract or removed capability, MINOR for a new plugin or a new
   backward-compatible capability in an existing one, PATCH for fixes/docs
   only. **State the version you propose and why, and get the user's
   go-ahead before continuing** — tagging and publishing a GitHub Release
   are outward-facing and awkward to fully undo, so this is not a step to
   guess silently through.

3. **Promote the root `CHANGELOG.md`.**
   - If `## [Unreleased]` doesn't exist, create it. If it exists but isn't
     the first section after the file's intro paragraphs (this file has
     drifted on that before — check), move it there. Don't reorder any
     *other* existing sections while doing this; fixing the one drift is
     in scope, re-litigating the whole file's history isn't.
   - Insert a new `## [X.Y.Z] - YYYY-MM-DD` section immediately below
     `## [Unreleased]`, written as a concise per-plugin summary (mirror the
     style of the existing `## [1.2.0]` entry — named sub-headings per
     plugin/area, short bullets, not a verbatim dump of every plugin
     changelog line).
   - Leave `## [Unreleased]`'s own `### Planned` roadmap subsection (if any)
     untouched — it carries forward release to release; only the
     already-shipped `### Added`/`### Changed`/`### Fixed` content (if any
     accumulated there) moves into the new version section.
   - Update the footer reference links: repoint `[Unreleased]:
     .../compare/vX.Y.Z...HEAD` and add `[X.Y.Z]:
     .../compare/v<prev>...vX.Y.Z`.

4. **Promote each touched plugin's own changelog.** For every
   `plugins/*/CHANGELOG.md` with real content under its `## Unreleased` (or
   equivalent) heading that you just folded into the root entry, rename
   that heading in place to that file's own convention — a dated header
   (`## YYYY-MM-DD`) if that's what its existing entries use, a SemVer
   header if that's what it uses instead. Don't impose one convention
   across plugins; follow each file's own precedent.

5. **Bump `.claude-plugin/marketplace.json`'s `metadata.version`** to the
   version from step 2. Leave every individual `plugins/*/plugin.json`
   `version` untouched unless a plugin's own maintainer is explicitly
   calling out a milestone for that plugin — a marketplace release and a
   single plugin's own version are independent judgment calls (see the
   cost-analyst 1.2.0 precedent, where only that plugin's own version
   moved, on its own schedule).

6. **Validate.** Run every command `CLAUDE.md` lists under "Validation"
   locally, exactly as CI runs them. All must pass before continuing —
   this promotes changelog/version files, so a schema or manifest
   regression here is as real a blocker as any other failing check.

7. **Commit.** `git commit -m "Promote changelog Unreleased to X.Y.Z for
   release"` (this exact message has shipped both prior releases — keep it
   traceable). Push directly to `main` — that's the established pattern for
   this specific administrative commit (see `git log` on the prior two
   releases; neither went through a PR), not an exception you're
   introducing.

8. **Tag and publish.** `git tag vX.Y.Z && git push origin vX.Y.Z`, then
   `gh release create vX.Y.Z --title "vX.Y.Z — <short theme>" --notes
   "<summary + link to CHANGELOG section>"` (mirror the title style of the
   existing `v1.2.0 — Model Right Sizer plugin` release).

9. **Open the docs PR.** Customer docs for CloudZero's AI Hub live in
   `Cloudzero/cloudzero-documentation`, default branch `v2.0` — branch from
   there, update whichever page(s) under `docs/Analyze Spend with AI
   Hub/` describe the capability that changed (e.g.
   `ai-model-right-sizer.md` for a model-right-sizer change), and open the
   PR against `v2.0`. Per the established process (see the
   `#tmp-model-right-sizer-announce` launch thread), this PR needs approval
   from a docs owner before it merges — open it and hand it off, don't
   merge it yourself. Say explicitly in your report which page(s) you
   touched and the PR link; "make sure the docs are updated" means this
   step ships, not just that the code shipped.

10. **Report.** State the version shipped, the tag + release URL, the docs
    PR URL and who needs to approve it, and anything from step 1 you
    flagged as an undocumented gap.

## Why this is scoped to *this* repo only

This mirrors the `model-right-sizer-install` skill's own discipline — it
does exactly one thing (release *this* marketplace) and doesn't try to be a
general-purpose release tool for other repos. If another CloudZero repo
wants the same discipline, that repo should write its own version of this
skill against its own changelog/versioning conventions rather than
importing this one — the mechanics above (dated vs. SemVer plugin
changelogs, the docs-repo handoff, the direct-push-to-main precedent) are
specific to how *this* repo has actually released twice, not a portable
abstraction.

## Related

- [`CLAUDE.md`](../../../CLAUDE.md) — the PR-ownership and validation
  mandate this skill assumes is already satisfied before it starts.
- [`CONTRIBUTING.md`](../../../CONTRIBUTING.md) — plugin/skill authoring
  conventions this skill's changelog promotion must stay consistent with.
- [`CHANGELOG.md`](../../../CHANGELOG.md) — what step 3 promotes.
