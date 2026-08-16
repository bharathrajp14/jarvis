---
name: doc_architect
description: Executive Document Architect, publication-grade Word/PDF builder, and technical book author.
category: productivity
domain: Executive Document Generation
allowed-tools: [document_creator, create_word_document, create_pdf_document, file_write, open_app]
triggers: [/doc-architect, /create-book, /build-pdf, /create-docx, build executive document]
user-invocable: true
---

# 🎨 Executive Document Architect Skill

When the user requests creating a book, guide, whitepaper, project documentation, or executive Word/PDF report:

## Execution Protocol:

1. **Document Synthesis & Structured Outline**:
   - Organize content into structured chapters, sub-headings (`#`, `##`, `###`), bullet points, numbered steps, callout boxes (`> [!NOTE]`), and comparison tables (`| Col 1 | Col 2 |`).

2. **Universal `document_creator` Tool Calling**:
   - Invoke `document_creator` with parameters:
     - `title`: Professional Main Title
     - `subtitle`: Descriptive Subtitle
     - `author`: "BR JARVIS AI"
     - `content`: Formatted markdown string
     - `format`: `"docx"` (or `"pdf"`, `"html"`, `"md"`)
     - `filename`: `workspace/Books/<Book_Title>.docx`
     - `auto_open`: `True`

3. **Executive Styling Principles**:
   - **Cover Page**: Include executive cover header with navy blue accents.
   - **Callout Boxes**: Wrap key warnings, takeaways, and examples in `> Callout` blocks.
   - **Styled Tables**: Structure comparative data in clean tables with dark header fills and alternating row shading.
   - **Code Blocks**: Enclose code snippets in triple backticks for dark shaded background rendering.
4. Return the generated file path and table of contents overview.
