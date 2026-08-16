---
name: researcher
description: Autonomous deep multi-source web researcher, article extractor, and structured markdown digest generator.
user_invocable: true
---

# 🔍 Automated Multi-Source Research Digest Skill

When the user asks for deep research, market analysis, topic exploration, or technical digests:

## Execution Steps:
1. **Multi-Query Web Search**: Use `web_search` to query 2-3 distinct perspectives on the topic.
2. **Page Content Extraction**: Fetch primary sources using `fetch_page` or `browser_auto_navigate_and_extract`.
3. **Synthesis & Fact Verification**: Synthesize findings across sources, highlighting key metrics, breakthroughs, and architectural insights.
4. **Structured Markdown Deliverable**: Produce a clean, publishable report formatted as follows:

```markdown
# 📊 Research Digest: [Topic Name]

## Executive Summary
- Key takeaway 1
- Key takeaway 2

## Key Findings & Data Points
- Detailed technical breakdown

## Comparative Analysis Table
| Metric / Feature | Option A | Option B |
| :--- | :--- | :--- |

## References & Sources
- Source 1 URL
```
