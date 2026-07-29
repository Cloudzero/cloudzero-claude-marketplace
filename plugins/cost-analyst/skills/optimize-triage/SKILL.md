---
name: optimize-triage
description: >
  Fetch top unaddressed CloudZero Optimize recommendations, dispatch parallel research
  agents per item, apply SRE critique, and surface actionable findings with confidence
  verdicts and per-resource report files. Read-only research only.
allowed-tools: Bash, Read, Glob, Grep, WebFetch, Task
---

# optimize-triage

Run a parallel, multi-agent cost optimization research sweep. Fetch the top unaddressed
high-value recommendations from CloudZero Optimize, dispatch concurrent research agents
to enrich each one, have each agent critique its own findings with a DevOps/SRE lens,
and surface only the recommendations that look genuinely actionable.

**This skill is research-only. No changes are made to any resource, configuration,
code, or cloud account at any point. Read access only.**

**If you hit a dead end, missing credentials, or an ambiguous signal — stop and ask.
Do not guess. Do not proceed past a blocker silently.**

---

## Prerequisites

This skill runs read-only cloud CLI commands (e.g. `aws ec2 describe-instances`,
`gcloud compute instances describe`, `kubectl get`). For defense-in-depth, configure a
**read-only IAM role or profile** for the cloud accounts being investigated. Avoid
running this skill with credentials that have write access to production resources.

---

## Phase 1 — Fetch and filter recommendations

Call `get_optimize_recs` directly (do not delegate) with `status = unaddressed`, sorted
by `cost_impact_last_30_days` descending. Fetch at least 25 results.

**Step 1a — Threshold.** If provided in invocation args (e.g. "threshold=200"), use it
silently. Otherwise default to **$500**. Do not prompt yet.

**Step 1b — Individuals.** A recommendation qualifies if `cost_impact_last_30_days >=
[threshold]`. Take up to the top 3 by savings descending.

**Step 1c — Clusters.** Group remaining recommendations by `recommendation_type_name` +
`account` (add `region` if still under threshold). Sum savings within each group. Keep
groups where combined savings >= [threshold] and no member qualified individually.

**Step 1d — Present and offer.** Show qualifying individuals in a table:

| # | Recommendation | Resource (Account) | Impact/mo | Effort |
|---|----------------|--------------------|-----------|--------|
| 1 | ...            | `resource` (alias) | $X,XXX    | Low    |

`Effort`: Low = config/policy change; Medium = code or IaC change; High = migration or
multi-team coordination.

If sub-threshold clusters exist, describe them in prose below the table (combined
savings + why collectively meaningful), then offer:

> "Want me to: 1. Research just the [N] item(s) over $[threshold], 2. Lower the
> threshold and include the clusters too, or 3. Something else?"

Skip the offer if no clusters exist. Stop if nothing qualifies at all.

Wait for the user's response. "2" or equivalent = include clusters (cap still 3 total).
"Keep agents unblocked" = run all phases in parallel without further confirmation.

---

## Phase 2 — Parallel research agents

Dispatch all agents concurrently as background agents. Each is independent.

### Agent naming

Use `resource-type-researcher` hyphenated labels (e.g. `s3-api-researcher`,
`rds-snapshot-researcher`, `gcp-storage-researcher`). Present a dispatch table first:

| Agent | Target | Est. Savings |
|-------|--------|--------------|
| [resource-type]-researcher | [Recommendation type] ([account-alias]) | $X,XXX/mo |
| ...   | ...    | ...          |

### Agent context

Pass each agent: recommendation type, cloud provider, account (with alias), region(s),
resource list (names/ARNs/IDs), resource type, combined monthly savings, oldest
`created` timestamp, and group size.

For groups, investigate a representative sample (up to 5). Label each sampled resource:
- **VALID**: signals corroborate the recommendation
- **INVALID**: clear "do not act" signal (active ticket, live dependency, recent commit,
  IaC-managed with no update path, already optimized)
- **UNCERTAIN**: insufficient data

Extrapolate from the sample to adjust the savings estimate for the full group.

### Agent instructions

1. **Load the CloudZero docs page** for this recommendation type — fetch
   https://docs.cloudzero.com/docs/optimize, find the matching slug, fetch it. Understand
   what the rec detects, the safe-to-act threshold, and "do not act" signals. If
   unavailable, proceed with general judgment.

2. **Run all applicable research checks below in parallel.** Read-only only.

3. **No access to a check** → note "not checked — no access" and continue.

4. **Check errors or loops** → stop that check, note the failure, continue.

---

### Check A — IaC

Search local IaC files for the resource identifier. Always single-quote interpolated
resource identifiers in shell commands to prevent metacharacter interpretation:

```
grep -r '[resource-id]' . \
  --include="*.tf" --include="*.tfvars" \
  --include="*.yaml" --include="*.yml" --include="*.json" \
  --include="*.ts" --include="*.py" 2>/dev/null
```

If found: resource is managed — changes must go through IaC, not applied directly. Note
the file(s) and relevant stanza. If a GitOps pipeline (Spacelift, Atlantis, ArgoCD) is
active, direct changes will be reverted.

---

### Check B — GitHub / source code

Search git history for the resource identifier and recent IaC changes:

```
git log --all --oneline -S '[resource-id]'
git log --all --oneline --since="90 days ago" -- "*.tf" "*.yaml" "*.yml"
```

For remote repos: identify the owning repo from service name or team tags, find the
default branch (`gh repo view [org]/[repo] --json defaultBranchRef`), then search
commits in a ±2-week window around `created`. For any suspicious commit fetch the PR
body to understand intent and affected files.

For service-driven recommendations (not orphaned resources), trace the trigger chain:
what calls this resource, how often, and from where? Focus on CronJobs, Airflow DAGs,
EventBridge rules, Step Functions, and Pub/Sub consumers. Note commit authors — they
are the right people to involve in remediation.

---

### Check C — Signals sweep (Jira, Slack, CloudZero)

**Jira:** Search for the resource identifier, resource name, and owning service/team.
An open "in use / do not touch" or active sprint ticket → SKIP signal. A closed cleanup
ticket → corroborates the recommendation. No tickets → consistent with abandonment.

**Slack** (if MCP available): Search for the resource identifier and name. Recent
mentions suggest active awareness or ongoing use.

**CloudZero cost trend:** Pull 60-day spend. Growing = more urgent. Declining = may
already be addressed upstream. Note which team, product, or cost center owns the spend.

---

### Check D — Cloud provider state

Query the cloud provider (read-only) to confirm current state and any existing
optimizations. Tailor to resource type:

- **S3**: `aws s3api get-bucket-lifecycle-configuration` + `list-bucket-intelligent-tiering-configurations`
- **EC2**: `aws ec2 describe-instances` + 30-day CloudWatch CPUUtilization
- **EBS**: `aws ec2 describe-volumes`
- **Elastic IP**: `aws ec2 describe-addresses`
- **RDS**: `aws rds describe-db-instances`
- **Azure**: `az vm show` / `az disk show` / `az storage account show`
- **GCP**: `gcloud compute instances describe` / `gcloud compute disks describe` / `gcloud storage buckets describe`

Note what is already optimized vs. what is missing — partial optimization is still a
valid finding.

---

### Check E — Category-specific

**Deletion / release** (idle VMs, disks, IPs, DBs): Check for dependencies (DNS,
security groups, load balancer targets, mount targets, snapshots). Verify genuinely idle
— not a quiet period. No owner tags = consistent with abandonment, but not proof.

**Rightsizing**: Confirm 30+ days of consistently low utilization — not a recent dip.
Check for ASG / HPA / managed node group (resize the template, not the instance). Check
recent deploy history.

**Reservations / commitments**: Confirm utilization rate justifies commitment length.
Check existing coverage. Flag upcoming migrations that could strand the commitment.

**Kubernetes**: `kubectl top pods`, `describe pod`, `get pvc --all-namespaces`,
`get hpa --all-namespaces`.

**API / egress costs**: These are often symptoms. Trace what is generating the calls
(CronJobs, DAGs, polling loops). A storage class change won't fix a hot polling loop.

**Storage tiering**: Distinguish transient vs. long-lived prefixes. Identify external
tables, ETL jobs, or warehouse queries that read from the bucket and would be affected
by retrieval latency from colder tiers.

**Upgrade / migration**: Confirm IaC won't revert the change. Note pre-upgrade steps,
compatibility validation, and change management requirements.

---

## Phase 3 — Internal validation (silent)

Do not narrate or label this phase in any output. The only output is the confidence
verdict.

Internally challenge findings on: **recency bias** (7 days ≠ idle; need 30+) —
**deploy cycle** (recent commits explaining low usage?) — **ownership ambiguity** (no
tags ≠ abandoned; team may just not tag) — **dependency shadows** (quiet failover
targets, quarterly-write buckets, VPN-anchoring EIPs) — **IaC revert risk** (direct
change will be undone on next apply) — **symptom vs. root cause** (polling loop driving
LIST costs won't be fixed by a tier change) — **savings confidence** (backward-looking
estimate vs. a changing cost trend).

Assign a verdict. For groups, apply to the valid subset only:

- **HIGH**: Multiple corroborating signals, no contradictions, clear owner, clean causal chain.
- **MEDIUM**: Mostly corroborated with one or more open questions.
- **LOW**: Significant contradictions or missing context — do not surface.
- **SKIP**: Clear "do not act" signal found — exclude from output.

**Mixed groups:** Split before assigning — surface VALID as a sub-group with adjusted
savings, count INVALID as SKIP, treat UNCERTAIN as MEDIUM. If the valid sub-group falls
below [threshold], suppress it too.

---

## Phase 4 — Progressive surfacing and rollup

### Progressive surfacing

Surface each result as soon as its agent completes. Every result message ends with:

> "Waiting on N more agents: [agent-name-1], [agent-name-2]..."

For each result show: agent name, recommendation type, 2–3 sentence summary (finding,
realistic savings, strongest supporting or contradicting signal), and confidence verdict.

### Rollup table

When the last agent completes, present:

| # | Recommendation | Resource (Account) | Claimed | Realistic | Verdict | Effort | Contact | Next Step |
|---|----------------|--------------------|---------|-----------|---------|--------|---------|-----------|

Only include HIGH and MEDIUM rows. One line below for suppressed items: "N suppressed:
[brief reason]." Then write report files (Phase 6).

### Post-analysis offer

> "Want me to dig deeper on any of these — check git logs for a specific item, look up
> team contacts, or anything else?"

---

## Phase 5 — Follow-up research loop

If the user asks deeper questions after the rollup, dispatch a new round of focused
parallel agents (e.g. `git-log-[resource]`, `[team]-contact-finder`). Surface results
progressively with the same "Waiting on N more agents..." pattern. If a finding
materially changes a confidence verdict, note it and update the rollup row.

---

## Phase 6 — Per-recommendation report files

Write `./optimize-triage-reports/[resource-name]-investigation-[date].md` for each HIGH
and MEDIUM result before presenting the rollup. Create the directory if it does not
exist. These reports may contain sensitive organizational data (account IDs, resource
identifiers, cost figures, team contacts, IaC configurations) — treat them as
confidential and do not commit them to version control.

Each report contains:

**Executive Summary** — 2–4 sentences: what the resource is, what it costs, what the
opportunity is. If realistic savings differs from CloudZero's estimate, explain why.

**Current State** — Resource details table (identifier, account, region, type, monthly
cost, owner tag, IaC location), cost trend table (one row per month), plain-language
trend interpretation, and existing config (IaC stanza or lifecycle rule, if found).

**What This Resource Is** — Purpose, data flow / trigger chain, downstream consumers,
active/legacy/uncertain status. Based on evidence found — if ownership is unclear, say so.

**Recommendation** — One paragraph describing the action and why. Include copy-pasteable
implementation details (code, commands, config) where gathered. Do not fabricate specifics.

**Estimated Savings** — Table: CloudZero estimate vs. conservative vs. optimistic, with
a brief explanation of any difference.

**Risks and Mitigations** — One subsection per evidence-backed risk. Name the actual
dependency, job, table, or compliance concern. No generic boilerplate.

**Suggested Rollout Plan** — Phased table: Phase 0 investigation (open questions to
answer first) → Phase 1 first safe change → Phase 2 monitor → Phase 3 follow-on if
applicable.

**File References** — IaC or source file paths, if found.

**Related Tickets** — Only if tickets were found.

**Questions for the Owner** — 3–6 specific, answerable questions based on actual open
questions from research. Not generic boilerplate.

---

Do not make any changes to any resource, configuration, code, or cloud account.
All actions in this skill are read-only.
