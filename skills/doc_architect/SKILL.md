---
name: doc_architect
description: Executive Document Architect, publication-grade Word/PDF book builder, and technical documentation engine.
user_invocable: true
---

# 🎨 Executive Document Architect Skill

When the user requests creating a book, guide, whitepaper, project documentation, or PDF/Word report:

## Execution Protocol:
1. **Document Synthesis & Outline**:
   - Organize content into structured chapters, sub-headings (`#`, `##`, `###`), bullet points, numbered steps, callout boxes (`> [!NOTE]`), and comparison tables (`| Col 1 | Col 2 |`).

2. **Use Universal `document_creator` Tool**:
   - Invoke `document_creator` with parameters:
     - `title`: Professional Main Title
     - `subtitle`: Descriptive Subtitle
     - `author`: "BR JARVIS AI"
     - `content`: Formatted markdown string
     - `format`: `"docx"` (or `"pdf"`, `"html"`, `"md"`)
     - `filename`: `workspace/Books/<Book_Title>.docx`
     - `auto_open`: `true`

3. **Executive Styling Principles**:
   - **Cover Page**: Include executive cover header with navy blue accents.
   - **Callout Boxes**: Wrap key warnings, takeaways, and examples in `> Callout` blocks.
   - **Styled Tables**: Structure comparative data in clean tables with dark header fills and alternating row shading.
   - **Code Blocks**: Enclose code snippets in triple backticks for dark shaded background rendering.
