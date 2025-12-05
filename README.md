# CloudZero Cost Analyst Plugin

[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE-OF-CONDUCT.md)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

CloudZero Cost Analyst is an AI-powered Claude Code plugin that provides comprehensive cloud cost analysis skills using CloudZero's MCP (Model Context Protocol) server. This plugin enables you to investigate cost spikes, analyze trends, compare spending, optimize services, and track cloud infrastructure costs—all through natural conversation with Claude.

**Key Features:**
- 🔍 **Cost Spike Investigation** - Identify and explain sudden cost increases
- 📊 **Trend Analysis** - Understand spending patterns and forecast future costs
- 🔄 **Cost Comparison** - Benchmark across time periods, teams, or environments
- 🎯 **Service Deep Dives** - Detailed analysis of specific cloud services
- 🏷️ **Tag Coverage Analysis** - Improve cost allocation and governance
- 👥 **Custom Dimension Analysis** - Business-aligned cost visibility
- 🚨 **Anomaly Detection** - Proactively identify unusual spending patterns
- 💰 **Top Cost Drivers** - Identify and prioritize optimization opportunities

**What's Included:**
- 8 specialized cost analysis skills powered by AI
- Pre-configured CloudZero MCP server integration
- Support for AWS, GCP, and Azure cost analysis
- Dynamic dimension discovery for your organization
- Showback/chargeback reporting capabilities

## Table of Contents

- [Plugin Marketplace](#plugin-marketplace)
- [Documentation](#documentation)
- [Installation](#installation)
- [Getting Started](#getting-started)
- [Available Skills](#available-skills)
- [Usage](#usage)
- [Contributing](#contributing)
- [Support + Feedback](#support--feedback)
- [Vulnerability Reporting](#vulnerability-reporting)
- [What is CloudZero?](#what-is-cloudzero)
- [License](#license)

## Plugin Marketplace

This repository serves as both a **Claude Code plugin** and a **plugin marketplace**. By adding this repository as a marketplace, you and your team get easy access to the Cost Analyst plugin and any future CloudZero plugins we release.

**Quick Start:**
```bash
/plugin marketplace add cloudzero/cloudzero-claude-cost-analyst
/plugin install cost-analyst@cloudzero
```

## Documentation

For more information about the tools and services used in this project:

- [Anthropic Claude](https://www.anthropic.com)
- [CloudZero Platform Docs](https://docs.cloudzero.com/)
- [CloudZero Blog](https://www.cloudzero.com/blog/)

## Installation

### Prerequisites

- Claude Code v1.0 or later installed on your system
- A CloudZero account with MCP server access
- Git installed (for git-based installation methods)

### Method 1: Install from Plugin Marketplace (Recommended)

Add the CloudZero plugin marketplace:

```bash
/plugin marketplace add cloudzero/cloudzero-claude-cost-analyst
```

Then install the Cost Analyst plugin:

```bash
/plugin install cost-analyst@cloudzero
```

**For Teams:** Add to `.claude/settings.json` for automatic marketplace availability:

```json
{
  "extraKnownMarketplaces": [
    "cloudzero/cloudzero-claude-cost-analyst"
  ]
}
```

**Alternative - Direct Git Installation:**

You can also install directly without adding the marketplace:

```bash
/plugin install git+https://github.com/cloudzero/cloudzero-claude-cost-analyst.git
```

### Method 2: Clone and Run Locally

Use this method if you want to modify the skills or work directly from the repository:

1. Clone this repository:

```bash
git clone https://github.com/cloudzero/cloudzero-claude-cost-analyst.git
cd cloudzero-claude-cost-analyst
```

2. Start Claude Code from this directory:

```bash
claude
```

The skills will be automatically discovered from the `.claude/skills/` directory (symlinked to `skills/`).

### MCP Server Configuration

After installation, configure the CloudZero MCP server by creating a `.mcp.json` file in your project:

```json
{
  "mcpServers": {
    "cloudzero": {
      "type": "http",
      "url": "https://mcp-server.discovery.cloudzero.com/mcp"
    }
  }
}
```

This repository includes a pre-configured `.mcp.json` file pointing to the CloudZero production MCP server.

## Getting Started

Once you've completed the installation steps above, you're ready to start analyzing your cloud costs with Claude!

The plugin comes pre-configured with:
- CloudZero MCP server connection
- 8 specialized cost analysis skills
- Dynamic dimension discovery for your organization

Simply start a conversation with Claude and ask cost-related questions. The appropriate skill will be automatically invoked based on your request.

## Available Skills

The CloudZero Cost Analyst plugin includes 8 AI-powered skills that Claude automatically uses based on your questions:

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

## Usage

### Authentication

The CloudZero MCP server handles authentication automatically.

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

## Contributing

We appreciate feedback and contribution to this repo! Before you get started, please see the following:

- [CloudZero's general contribution guidelines](GENERAL-CONTRIBUTING.md)
- [CloudZero's code of conduct guidelines](CODE-OF-CONDUCT.md)
- [This repo's contribution guide](CONTRIBUTING.md)

## Support + Feedback

- Use [GitHub Issues](https://github.com/cloudzero/cloudzero-claude-cost-analyst/issues) for code-level support and bug reports
- Contact [support@cloudzero.com](mailto:support@cloudzero.com) for CloudZero platform questions and account-specific issues

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

## License

This project is licensed under the Apache 2.0 [LICENSE](LICENSE).
