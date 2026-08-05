# CloudZero

Welcome to **CloudZero**, the CloudZero plugin marketplace for Claude Code! This repository hosts AI-powered plugins for cloud and AI cost intelligence: investigate cost spikes, analyze trends, compare spending, optimize services, and track cloud infrastructure costs using CloudZero's MCP (Model Context Protocol) server—plus right-size which Claude model each AI task should run on. All through natural conversation with Claude.

**Key Features:**
- 🔍 **Cost Spike Investigation** - Identify and explain sudden cost increases
- 📊 **Trend Analysis** - Understand spending patterns and forecast future costs
- 🔄 **Cost Comparison** - Benchmark across time periods, teams, or environments
- 🎯 **Service Deep Dives** - Detailed analysis of specific cloud services
- 🏷️ **Tag Coverage Analysis** - Improve cost allocation and governance
- 👥 **Custom Dimension Analysis** - Business-aligned cost visibility
- 🚨 **Anomaly Detection** - Proactively identify unusual spending patterns
- 💰 **Top Cost Drivers** - Identify and prioritize optimization opportunities
- 📝 **Diff Cost Projection** - Estimate cost impact of code changes in PRs and branches
- 🏗️ **Cost Projection** - Project monthly cost of infrastructure definitions before deployment
- 🧰 **Optimize Triage** - Research and validate CloudZero Optimize recommendations with parallel agents
- 🧮 **Model Right-Sizing** - Pick the smallest Claude model that clears the bar for each AI task

## Available Plugins

### Cost Analyst Plugin
The flagship plugin providing comprehensive cost analysis capabilities:
- 11 specialized cost analysis skills powered by AI
- Pre-configured CloudZero MCP server integration
- Dynamic dimension discovery for your organization
- Showback/chargeback reporting capabilities

### Model Right Sizer Plugin
A model-selection economist for Claude Code that keeps AI spend as intentional as cloud spend:
- The `model-right-sizer` agent scores each task on effectiveness need vs. efficiency pressure vs. difficulty, and recommends the smallest Claude model (plus effort and token budget) that clears the bar
- Runs as a bookend around work: a right-sizing blueprint before, a model-usage report after
- Learns from what its picks actually cost: a machine-wide calibration ledger, read by every session in every repo, so the cost of a wrong pick informs the next one instead of being thrown away
- Companion skills to preview the routing map for an intent (`model-right-sizer-dryrun`), stamp a standing right-sizing mandate onto a repo (`model-right-sizer-install`), feed/read the calibration ledger (`model-right-sizer-calibrate`), audit whether that ledger is actually improving the picks (`model-right-sizer-eval`), and verify the memory really is installed and universal (`model-right-sizer-verify`)

See the [Model Right Sizer README](plugins/model-right-sizer/README.md) for full details.

## Table of Contents

- [Repository Structure](#repository-structure)
- [Documentation](#documentation)
- [Installation](#installation)
- [Available Skills](#available-skills)
- [Usage](#usage)
- [Support + Feedback](#support--feedback)
- [Vulnerability Reporting](#vulnerability-reporting)
- [What is CloudZero?](#what-is-cloudzero)

## Repository Structure

This repository is organized to support multiple plugins:

```
cloudzero-claude-marketplace/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace configuration
├── plugins/
│   ├── cost-analyst/             # Cost Analyst plugin
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json       # Plugin manifest
│   │   ├── .mcp.json             # MCP server configuration
│   │   ├── skills/               # Cost analysis skills
│   │   └── references/           # Shared reference documentation
│   └── model-right-sizer/        # Model Right Sizer plugin
│       ├── .claude-plugin/
│       │   └── plugin.json       # Plugin manifest
│       ├── agents/               # The model-right-sizer agent
│       ├── skills/               # Companion install/dry-run/calibrate/eval/verify skills
│       ├── templates/            # Learned-skill seed, ledger schema, SkillOpt config
│       ├── eval/                 # Held-out routing tasks + the audit harness rubric
│       └── README.md             # Plugin documentation
├── scripts/                      # CI validators (manifests, agent files)
├── tests/                        # Tests for the validators
├── README.md
└── ...
```

Each plugin in the `plugins/` directory is self-contained with its own configuration, skills, and dependencies.

## Documentation

For more information about the tools and services used in this project:

- [Anthropic Claude](https://www.anthropic.com)
- [CloudZero Platform Docs](https://docs.cloudzero.com/)
- [CloudZero Blog](https://www.cloudzero.com/blog/)

## Installation

Add the CloudZero marketplace to Claude Code once, then install whichever plugins you want from it:

```
/plugin marketplace add cloudzero/cloudzero-claude-marketplace
```

Adding the marketplace makes every plugin in this repository available. It does not install them by itself — install each plugin you want:

```
/plugin install cost-analyst@cloudzero
/plugin install model-right-sizer@cloudzero
```

Installing `cost-analyst@cloudzero` gives you the 11 cost analysis skills and the pre-configured CloudZero MCP server. Installing `model-right-sizer@cloudzero` gives you the model-right-sizer agent and its five companion skills.

For platform setup and more installation guidance, see the [CloudZero AI Hub](https://docs.cloudzero.com/docs/ai-getting-started).

## Available Skills

### Cost Analyst Plugin

The CloudZero Cost Analyst plugin includes 11 AI-powered skills that Claude automatically uses based on your questions:

### 1. Cost Spike Investigation
**Triggered by:** "What caused the cost spike?", "Why did costs increase?", "Investigate cost jump"

Analyzes sudden cost increases by comparing recent spending to baselines and identifying which services, accounts, or resources are responsible.

**Example:**
```
"Our AWS costs spiked last week. Can you investigate what happened?"
```

### 2. Top Cost Drivers
**Triggered by:** "What are my biggest costs?", "Show top spending", "Where is money going?"

Identifies and ranks the highest cost contributors across services, accounts, teams, and regions to prioritize optimization efforts.

**Example:**
```
"What are my top 10 cost drivers this month?"
```

### 3. Cost Trend Analysis
**Triggered by:** "How are costs trending?", "Show cost growth", "Forecast spending"

Analyzes cost trends over time to identify patterns, growth rates, seasonality, and forecast future spending.

**Example:**
```
"Analyze my cost trends over the last 90 days and forecast next month"
```

### 4. Cost Comparison
**Triggered by:** "Compare costs between...", "Production vs staging costs", "This month vs last month"

Compares costs across time periods, environments, accounts, regions, or teams to understand variations and benchmark efficiency.

**Example:**
```
"Compare production costs to staging and development environments"
```

### 5. Service Cost Deep Dive
**Triggered by:** "Analyze EC2 costs", "Deep dive into RDS", "Break down S3 spending"

Performs detailed analysis of specific cloud services, breaking down by usage types, resources, regions, and identifying optimization opportunities.

**Example:**
```
"Do a deep dive on our EC2 costs and identify optimization opportunities"
```

### 6. Tag Coverage Analysis
**Triggered by:** "Check tag coverage", "Show untagged resources", "Tagging quality"

Evaluates tagging quality and coverage to identify untagged resources, calculate coverage percentages, and improve cost allocation.

**Example:**
```
"What's our tag coverage and which resources are untagged?"
```

### 7. Custom Dimension Analysis
**Triggered by:** "Costs by team", "Spending by product", "Show business unit costs"

Analyzes costs using organization-specific custom dimensions (teams, products, features) for business-aligned visibility and showback/chargeback.

**Example:**
```
"Show me costs broken down by team for the last month"
```

### 8. Cost Anomaly Detection
**Triggered by:** "Detect anomalies", "Find unusual spending", "Check for cost issues"

Proactively scans for cost anomalies, unusual patterns, and irregularities that may indicate waste, misconfiguration, or security issues.

**Example:**
```
"Scan for any cost anomalies or unusual spending patterns"
```

### 9. Diff Cost Projection
**Triggered by:** "Cost impact of this PR", "What will this branch cost?", "Estimate cost of my changes"

Analyzes code diffs (PRs, branches, workspace changes) for infrastructure cost impact. Detects Terraform, CDK, CloudFormation, SAM, Kubernetes, scaling, and application code changes that affect cloud spending.

**Example:**
```
/diff-cost-projection 456
"What's the cost impact of the changes on my current branch?"
```

### 10. Cost Projection
**Triggered by:** "How much will this stack cost?", "Project cost of this Terraform", "Estimate cost of deployment.cdk"

Reads infrastructure-as-code definitions (Terraform, CDK, CloudFormation, SAM) and projects monthly cost. Enumerates resources, queries CloudZero for existing spend, looks up pricing for new resources, and produces a line-item breakdown.

**Example:**
```
/cost-projection terraform/production/
"How much will this CDK stack cost to deploy?"
```

### 11. Optimize Triage
**Triggered by:** "Triage our Optimize recommendations", "Which optimization recommendations are actionable?", "Research our top savings opportunities"

Fetches top unaddressed CloudZero Optimize recommendations, dispatches parallel research agents per item with an SRE critique pass, and surfaces the genuinely actionable ones with confidence verdicts. Research-only — but note it is the one skill granted `Bash` access, used for read-only cloud CLI commands (e.g. `aws ec2 describe-instances`); run it with read-only credentials.

**Example:**
```
"Triage our top CloudZero Optimize recommendations and tell me which are actually actionable"
```

### Model Right Sizer Plugin

The Model Right Sizer plugin includes one agent and two skills:

#### The `model-right-sizer` Agent
**Triggered by:** "Blueprint this task", "Which model should this run on?", "Give me a usage report"

A read-only model-selection economist. Before work starts it produces a right-sizing blueprint — a task→model→effort→budget→confidence routing table biased toward the smallest Claude model that clears the bar. After work closes it produces a usage report comparing recommended vs. actual model spend.

**Example:**
```
"Blueprint this PR: refactor a REST endpoint, add tests, update docs — which model should each part run on?"
```

#### Model Right Sizer Dry Run
**Triggered by:** "Dry-run the right-sizer on...", "What's the map for...", "How would you route..."

Previews the model-routing map for a free-text intent without building anything — the what-would-this-cost lever, safe to run against any idea.

**Example:**
```
"Dry-run the right-sizer on: build a Slack bot that summarizes daily standup threads"
```

#### Model Right Sizer Install
**Triggered by:** "Install model-right-sizer in this repo", "Add the right-sizer mandate here"

Stamps a standing mandate onto the current repo's `CLAUDE.md` so every substantive task consults the `model-right-sizer` agent before and after the work, and — after asking — seeds the machine-wide learning loop (the `model-right-sizer-learned` skill, its calibration ledger, and a matching block in the user-level `CLAUDE.md`). Idempotent and append-only: a re-run refreshes wording without ever touching accumulated learnings.

**Example:**
```
"Install model-right-sizer in this repo"
```

#### Model Right Sizer Calibrate
**Triggered by:** "Log this run", "What has the right-sizer learned?", "Review the staged skill proposal"

Feeds and reads the machine-wide calibration ledger — the memory that keeps every blueprint from starting at zero. `append` turns a usage report into schema-valid rows, `summary` aggregates them by task shape, `review` adopts a staged SkillOpt-Sleep proposal only on an explicit yes. Rows record task *shapes*, never repo names, paths, ticket ids, code, or customer data — which is what makes one shared ledger safe to read from every repo.

**Example:**
```
"What has the right-sizer learned about code review?"
```

#### Model Right Sizer Verify
**Triggered by:** "Is the learning loop actually installed?", "Verify universal preservation", "Does my other repo see this?"

Proves the install is real rather than merely reported: **discovery** (probe a session in a throwaway repo unrelated to the plugin, with a canary token so you prove the content arrived and not just the name), **preservation** (re-install twice and confirm accumulated learnings survive byte-for-byte while the protected regions refresh), and **integrity** (every ledger row schema-clean and free of repo-identifying prose). Run it before the eval harness.

**Example:**
```
"Verify the right-sizer memory is discoverable from my other repos"
```

#### Model Right Sizer Eval
**Triggered by:** "Does the learning loop actually work?", "Audit the right-sizer", "Benchmark the calibration ledger"

A blind, controlled audit of whether accumulated calibration measurably improves routing — three rounds, a no-memory control arm every round, disjoint task sets so a gain is transfer rather than recall, and the agent sandboxed away from this repo so it can't read the answers. Built to be able to return "no": its own first run saturated at 24/24 in both arms, and it now opens with the gate that catches that before you spend anything.

**Example:**
```
"Audit whether the right-sizer's ledger is actually improving its picks"
```

See the [Model Right Sizer README](plugins/model-right-sizer/README.md) for the full documentation.

## Usage

### Example Workflows

**Monthly Cost Review:**
```
"Run an anomaly detection scan, then show me my top cost drivers and any trends"
```

**Cost Spike Response:**
```
"We had a cost spike last Tuesday. Investigate what caused it and recommend actions"
```

**Service Optimization:**
```
"Do a deep dive on our RDS costs and identify optimization opportunities"
```

**Showback Reporting:**
```
"Generate a cost breakdown by team for Q4 including service details"
```

**Tag Governance:**
```
"Analyze our tag coverage and prioritize resources that need tagging"
```

### Tips for Best Results

1. **Be Specific:** Include time periods, services, or dimensions you want to analyze
2. **Ask Follow-ups:** The skills work together - ask Claude to investigate further on interesting findings
3. **Request Actions:** Ask for specific recommendations and next steps
4. **Combine Skills:** Complex analyses often benefit from multiple skills working together
5. **Use Your Organization's Terms:** The skills understand your custom dimensions (teams, products, etc.)

### How Skills Work

Skills are automatically invoked by Claude based on your natural language requests. You don't need to explicitly call them - just ask your cost analysis question naturally, and Claude will:

1. Read your organization context from CloudZero
2. Select the appropriate skill(s) to answer your question
3. Query CloudZero's cost data via the MCP server
4. Analyze the results and provide insights
5. Recommend specific actions based on findings

All skills follow these best practices:
- Always read organization context first for accurate analysis
- Use your organization's specific dimensions and tags
- Provide actionable recommendations with dollar impacts
- Support both technical and business-aligned reporting

## Support + Feedback

Contact [support@cloudzero.com](mailto:support@cloudzero.com) for CloudZero platform questions and account-specific issues

## Vulnerability Reporting

Please do not report security vulnerabilities on the public GitHub issue tracker. Email [security@cloudzero.com](mailto:security@cloudzero.com) instead.

## What is CloudZero?

CloudZero is the only cloud cost intelligence platform that puts engineering in control by connecting technical decisions to business results:

- [Cost Allocation And Tagging](https://www.cloudzero.com/tour/allocation) - Organize and allocate cloud spend in new ways, increase tagging coverage, or work on showback.
- [Kubernetes Cost Visibility](https://www.cloudzero.com/tour/kubernetes) - Understand your Kubernetes spend alongside total spend across containerized and non-containerized environments.
- [FinOps And Financial Reporting](https://www.cloudzero.com/tour/finops) - Operationalize reporting on metrics such as cost per customer, COGS, gross margin. Forecast spend, reconcile invoices and easily investigate variance.
- [Engineering Accountability](https://www.cloudzero.com/tour/engineering) - Foster a cost-conscious culture, where engineers understand spend, proactively consider cost, and get immediate feedback with fewer interruptions and faster and more efficient innovation.
- [Optimization And Reducing Waste](https://www.cloudzero.com/tour/optimization) - Focus on immediately reducing spend by understanding where we have waste, inefficiencies, and discounting opportunities.

Learn more about [CloudZero](https://www.cloudzero.com/) on our website [www.cloudzero.com](https://www.cloudzero.com/)
