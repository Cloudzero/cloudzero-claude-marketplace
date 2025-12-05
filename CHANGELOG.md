# Changelog

All notable changes to the CloudZero Cost Analyst Plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-05

### Added

#### Core Plugin Infrastructure
- Initial release of CloudZero Cost Analyst Plugin for Claude Code
- Plugin packaging with `.claude-plugin/plugin.json` manifest
- Dual installation support: as plugin or cloned repository
- Pre-configured CloudZero MCP server integration via `.mcp.json`

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

#### Features

- **Dynamic Dimension Discovery**: All skills automatically discover and use organization-specific dimensions via `get_organization_context`
- **CloudZero MCP Integration**: Full integration with CloudZero's Model Context Protocol server
- **Multi-Cloud Support**: Analysis capabilities for AWS, GCP, and Azure costs
- **Natural Language Interface**: Skills automatically invoked based on conversational requests
- **Comprehensive Documentation**: Detailed SKILL.md files with workflows, examples, and best practices
- **Organization Context Awareness**: All skills prioritize reading organization-specific context for accurate analysis

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

### Installation Methods

- Direct git URL installation: `/plugin install git+https://github.com/cloudzero/cloudzero-claude-cost-analyst.git`
- Marketplace installation: `/plugin marketplace add cloudzero/cloudzero-claude-cost-analyst`
- Team automation via settings.json configuration
- Local clone and run from repository root

---

## [Unreleased]

### Planned

- Additional specialized skills for Reserved Instance analysis
- Savings Plan optimization skill
- Budget tracking and alerting integration
- Cost allocation rule recommendations
- Interactive cost report generation
- Integration with additional CloudZero features

---

[Unreleased]: https://github.com/cloudzero/cloudzero-claude-cost-analyst/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/cloudzero/cloudzero-claude-cost-analyst/releases/tag/v1.0.0
