---
name: finance-skills
description: 'Router/index for the 2 finance skills bundled in this plugin: financial-analyst
  (ratio analysis, DCF valuation, budget variance, rolling forecasts) and saas-metrics-coach
  (ARR/MRR, churn, CAC/LTV, NRR, quick ratio). Use when a finance request doesn''t
  obviously match one skill and you need to pick the right one (e.g., ''analyze these
  financials'', ''how healthy are my SaaS metrics'').'
category: finance
domain: Finance
triggers:
- /finance-skills
- run finance skills
- finance skills skill
tools:
- create_excel_sheet
- document_creator
- web_search
- batch_file_ops
argument-hint: '[finance skills details]'
when_to_use: Use when user requests finance skills guidance or task execution.
user-invocable: true
context: inline
---

# Finance Skills — Router

This plugin bundles **2 finance skills** (this router is the 3rd folder under `finance/skills/`). Each skill is self-contained.

## Routing table

| Request signals | Skill | Path |
|---|---|---|
| Ratio analysis, DCF valuation, budget variance, driver-based forecasts | financial-analyst | `skills/financial-analyst/` |
| ARR/MRR, churn, CAC/LTV, NRR, quick ratio, SaaS benchmarks | saas-metrics-coach | `skills/saas-metrics-coach/` |

If both match (e.g., "value my SaaS company"), ask whether the user wants statement-level analysis (financial-analyst) or SaaS operating metrics (saas-metrics-coach).

## Quick start

```bash
# Example: route a statement-analysis request
cat finance/skills/financial-analyst/SKILL.md
python3 finance/skills/financial-analyst/scripts/ratio_calculator.py --help

# Or a SaaS metrics request
python3 finance/skills/saas-metrics-coach/scripts/metrics_calculator.py --help
```

## Related (packaged separately, not in this bundle)

- `finance/business-investment-advisor/` — investment thesis evaluation, ROI modeling (prompt-only skill, separate nested plugin)
- Root commands `/financial-health` and `/saas-health` wrap these skills' scripts.

## Rules

- Route to exactly one skill, then follow that skill's workflow. This router ships no tools of its own.
- Always validate financial outputs against the user's source data; outputs are analysis support, not investment advice.
