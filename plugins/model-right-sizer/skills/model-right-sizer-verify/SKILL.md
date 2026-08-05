---
name: model-right-sizer-verify
description: >-
  Prove the model-right-sizer learning loop is actually installed, actually
  universal, and actually preserved — three checks that a passing install
  report cannot substitute for. DISCOVERY spawns a session in a fresh,
  unrelated repo and confirms the learned skill is found there with its
  content intact, using a canary token. PRESERVATION re-runs the installer
  and confirms accumulated learnings survive byte-for-byte while the
  protected regions refresh. INTEGRITY validates every ledger row against
  the schema and scans for repo-identifying leakage. Use after installing
  the loop, after upgrading the plugin, or whenever someone asks "is this
  actually working in my other repos".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-verify — prove the install is real

`model-right-sizer-install` reports what it wrote. That is not the same as the
loop working. Three claims sit between "files written" and "working", and each
one fails silently:

| Claim | How it fails silently |
|---|---|
| **Universal** — every session in every repo reads it | The skill is written somewhere the runtime doesn't scan. Sessions simply never mention it, and nothing errors. |
| **Preserved** — a re-install doesn't destroy learnings | The one artifact in this system that cannot be regenerated gets overwritten by a template. You find out when the ledger reads as new. |
| **Repo-agnostic** — rows are safe to read anywhere | A row carries a repo name or path. Nothing breaks; the evidence is just wrong everywhere else, and quietly leaks. |

This skill checks all three. Run it after install, after a plugin upgrade, and
any time someone asks whether the loop is live.

## Check 1 — DISCOVERY (the universal claim)

The only honest test is a session in a repo that has nothing to do with this
plugin. **The default probe writes nothing at all** — see the design note below
for why that matters more than it sounds like it should.

1. **Build a throwaway repo** outside your working tree: `git init` a scratch
   directory with a file or two, **no `CLAUDE.md`**, no plugin, no mention of
   model-right-sizer anywhere in it.

2. **Pick the probe based on whether the learned skill has anything to lose.**

   | State of the learned skill | Probe | Writes? |
   |---|---|---|
   | Has accumulated learnings, or a non-empty ledger | **read-only** (default) | none |
   | Pristine seed with an empty ledger | canary (below) | yes, but nothing is at risk |

3. **The read-only probe.** Ask for facts that exist *only* in the local
   install and are therefore unavailable to a model reciting the published
   template — the ledger's row count and its most recent row id:

   ```
   cd /path/to/throwaway-repo
   claude -p --allowedTools "Read,Glob,Skill" <<'EOF'
   Do you have a skill available named model-right-sizer-learned? Answer in exactly this shape and nothing else:
   DISCOVERED: yes|no
   SOURCE: <where it came from, or n/a>
   LEDGER_ROWS: <how many rows in its ledger.jsonl, or n/a>
   LATEST_ROW_ID: <the id of the last row in ledger.jsonl, or n/a>
   FIRST_LEARNING_ID: <the first learning id listed under Calibration learnings, or n/a>
   EOF
   ```

   **Pass = all five lines correct**, checked against the file yourself. The row
   count and latest id are local, private, and change over time, so getting them
   right is only possible by actually reading the install — which is the same
   thing a canary proves, without touching a shared file.

4. **The canary probe — only for a pristine install.** When the skill is the
   untouched seed and the ledger is empty, there are no accumulated learnings
   for a concurrent write to destroy, so planting a canary is safe. Everything
   in the published seed is also in this repo, so a unique token is the only way
   to prove content was read rather than recited. Sweep any leftover
   `verify-canary` block first, then:

   ```bash
   SKILL=~/.claude/skills/model-right-sizer-learned/SKILL.md
   cleanup() {
     # Range-delete ONLY when both delimiters are present. An unpaired BEGIN
     # would make sed cut from there to EOF.
     if grep -q 'verify-canary:BEGIN' "$SKILL" && grep -q 'verify-canary:END' "$SKILL"; then
       sed -i.tmp '/verify-canary:BEGIN/,/verify-canary:END/d' "$SKILL" && rm -f "$SKILL.tmp"
     elif grep -q 'verify-canary:' "$SKILL"; then
       echo "UNPAIRED canary delimiter in $SKILL — refusing to range-delete." >&2
       return 1
     fi
   }
   trap 'acquire && cleanup; release' EXIT INT TERM

   # INSERT: hold the shared writer lock across read -> modify -> write.
   # The lock is what makes this safe. The rename keeps the file from ever
   # being observed half-written by a *reader*, which the lock does not cover.
   acquire || exit 1
   add_canary "$SKILL" > "$SKILL.new" && mv -f "$SKILL.new" "$SKILL"
   release

   # ...run the probe UNLOCKED — it takes minutes, and holding the lock across
   # it would block every other writer on the machine, which is worse...
   ```

   Both the insert and the cleanup delete take the shared **writer lock** (see
   below), so they are serialized against a concurrent `install` refresh or
   `calibrate review` adoption rather than racing them. The probe itself runs
   **unlocked** — it takes minutes, and holding a lock across it would block
   every other writer on the machine, which is worse than the problem.

   The canary is tagged `provenance: canary (NOT evidence)` inside
   `verify-canary:BEGIN/END` delimiters, so a survivor is inert and removable
   deterministically.

   > **Never leave canary content behind.** A fabricated learning sitting in a
   > real learned skill is indistinguishable from a measured one, and the agent
   > will cite it with the authority of evidence. Cleanup is part of the test,
   > not an optional step afterwards — which is why it is a shell trap
   > registered *before* the write, a delete of a delimited block rather than a
   > snapshot restore, and confirmed by grep rather than assumed. Every entry
   > point to the loop (`model-right-sizer-install` included) also sweeps a
   > leftover block, so an aborted run is cleaned up by the next touch from any
   > direction.

5. **Confirm the install is untouched.** Whichever probe you ran, end by
   confirming no canary token remains anywhere under the learned skill.

## The writer lock — every writer of the learned skill takes it

`~/.claude/skills/model-right-sizer-learned/` is machine-wide, so it has
multiple independent writers: `model-right-sizer-install` refreshing the
protected regions, `model-right-sizer-calibrate review` adopting a staged
learning, and `model-right-sizer-verify` inserting or removing a canary. Without
a shared lock, any two of those racing loses one side's work — and a
compare-and-swap doesn't fix it, because check-then-act is not atomic: another
writer can land between the check and the write no matter how small the window.

**Contract: take `.skill.lock` in the skill directory for the whole
read → modify → write of `SKILL.md`, and release it even on failure.** Hold it
for the write only — never across a long-running probe or an interactive review.

```bash
LOCKDIR=~/.claude/skills/model-right-sizer-learned/.skill.lock
acquire() {                       # mkdir is atomic on POSIX; flock is not portable to macOS
  for _ in $(seq 1 50); do
    mkdir "$LOCKDIR" 2>/dev/null && { trap 'rmdir "$LOCKDIR" 2>/dev/null' EXIT INT TERM; return 0; }
    sleep 0.1
  done
  echo "could not acquire $LOCKDIR — another writer is active, or a stale lock remains" >&2
  return 1
}
release() { rmdir "$LOCKDIR" 2>/dev/null; }
```

A writer that cannot take the lock **aborts and reports**; it never proceeds
unlocked. `ledger.jsonl` is a separate concern — it is append-only with
nonce-bearing ids, so it needs no lock (see `model-right-sizer-calibrate`).

### Why the default is read-only

This check went through five rounds of review, and every finding was a
different symptom of one root cause: **the probe was mutating a file that other
sessions write.** Lost updates, torn writes, snapshot rollbacks, orphan
delimiters — each fix exposed the next layer, because a read-modify-write
against shared mutable state cannot be made safe by adding more careful writes.

The learned skill is machine-wide **by design**, so a concurrent
`model-right-sizer-calibrate review` adoption or an installer refresh is normal
traffic, not an unlucky coincidence. Even a compare-and-swap only narrows the
window — it can't close it without holding a lock across a multi-minute probe
session, which would be worse.

So the fix is not a better write. It is **not writing**: derive the proof from
data the install already has. The canary survives only for the pristine case,
where by definition there is nothing to lose, and even there it is
compare-and-swap guarded.

**Two traps worth knowing before you run it:**

- **Do not try to sandbox this with `CLAUDE_CONFIG_DIR`.** Relocating the config
  directory also relocates authentication away from the OS keychain, and the
  probe fails with `Not logged in` rather than telling you anything about
  discovery. The test has to run against the real config directory.
- **Therefore it reads the user's actual environment** — confirm with them
  first. With the read-only probe there is nothing to clean up, which is most of
  the point.

## Check 2 — PRESERVATION (the re-install claim)

The installer's contract is that a re-run refreshes the frontmatter and the two
protected regions while leaving everything between them untouched. Verify it
rather than trusting it:

1. Note the current learned `SKILL.md` and `ledger.jsonl` (hash them).
2. Append a sentinel line to the **trainable body** — between
   `<!-- SLOW_UPDATE_END -->` and `<!-- APPENDIX_START -->`.
3. Re-run `model-right-sizer-install`.
4. **Pass:** the sentinel survives verbatim, `ledger.jsonl` is byte-identical,
   and both protected regions now match the current template.
5. Re-run once more and confirm the file is **byte-identical** to step 4 —
   idempotency is the property most likely to regress.
6. **Also test the tampered case:** remove one protected marker and re-run. The
   installer must *report* the unbalanced markers and leave the file alone, not
   guess where the region should go.

## Check 3 — INTEGRITY (the repo-agnostic claim)

Validate every row in `ledger.jsonl` against
[`templates/ledger-entry.schema.json`](../../templates/ledger-entry.schema.json).
That catches unknown keys and off-vocabulary `stage_kind` values — but be clear
about the boundary: **schema validation is not content sanitization.** `lesson`
and both model fields accept arbitrary strings, so a row naming a repo passes
validation cleanly.

So the automated half cannot finish this check. **Read every `lesson` field
yourself.** This human/agent read is the *only* control on free-text leakage
after the fact, which is why INTEGRITY is a check in its own right rather than
a line item under "run the validator".

Flag any row whose lesson names a repo, path, ticket, service, or person. A
leaked row isn't just a disclosure problem — it is *wrong evidence* in every
other repo that reads it.

## Known result — 2026-08-05, plugin 0.2.0

**Check 1 passed.** Probe run from a freshly `git init`-ed scratch repo with no
`CLAUDE.md`, no plugin, and no reference to this marketplace:

```
DISCOVERED:   yes
SOURCE:       ~/.claude/skills/model-right-sizer-learned/
CANARY:       HALYARD-31
LEDGER_ROWS:  1
```

Corroborated live: the skill also appeared in a *separate*, already-running
session's available-skills list moments after installation — cross-session
propagation observed, not inferred. The test install was removed afterward.

**Check 2 passed** against a simulated home directory across a fresh install, a
re-install with accumulated learnings present, a third idempotency run, and a
tampered-marker case (correctly refused).

**Check 3 passed** on synthetic rows: well-formed and deliberately sparse rows
validate; rows carrying a `repo` field, a nested file path, an off-vocabulary
`stage_kind`, a PR-style id, or a session-identifying timestamp are rejected.

## Related

- [`model-right-sizer-install`](../model-right-sizer-install/SKILL.md) — writes
  what this skill verifies.
- [`model-right-sizer-eval`](../model-right-sizer-eval/SKILL.md) — the next
  question. This skill asks *is the memory there*; that one asks *does it
  change the picks*. Run this one first: an eval against a memory that was
  never discovered measures nothing.
- [`model-right-sizer-calibrate`](../model-right-sizer-calibrate/SKILL.md) —
  `summary` is a fast informal read on whether the ledger is accumulating.
