---
name: researcher
description: Autonomous deep multi-source web researcher, article extractor, and structured markdown digest generator.
category: research
domain: Web Intelligence
allowed-tools: [web_search, fetch_page, fetch_raw, browser_auto_navigate_and_extract, file_write]
triggers: [/deep-research, /research-digest, /web-intel, deep web research]
user-invocable: true
---

# 🔍 Automated Multi-Source Research Digest Skill

When the user asks for deep research, market analysis, topic exploration, or technical digests:

## Execution Protocol:
1. **Multi-Query Web Search**: Use `web_search` to query 2-3 distinct perspectives on the topic (technical architecture, industry benchmarks, practical challenges).
2. **Page Content Extraction**: Fetch primary sources using `fetch_page` or `browser_auto_navigate_and_extract`.
3. **Synthesis & Fact Verification**: Synthesize findings across sources, highlighting key metrics, breakthroughs, and architectural insights.
4. **Structured Markdown Deliverable**: Produce a clean, publishable report formatted as follows:

```markdown
# 📊 Research Digest: [Topic Name]

## Executive Summary
- Key breakthrough / finding 1
- Key breakthrough / finding 2

## Key Findings & Deep Dive
- Detailed technical breakdown with citations

## Comparative Analysis Table
| Metric / Feature | Approach A | Approach B |
| :--- | :--- | :--- |

## Verified Sources & References
- [Source Title](https://...)
```
