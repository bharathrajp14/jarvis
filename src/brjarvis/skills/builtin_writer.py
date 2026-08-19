# skills/builtin_writer.py — BR-JARVIS MK37 AI Writing & Document Generation Skills
"""
Professional writing assistant and executive document generation skills for BR-JARVIS MK37.
Covers: executive briefs, technical documentation, Word/PDF reports, essay drafting,
email drafting, blog posts, translation, and proofreading.
"""

from __future__ import annotations

from .loader import SkillDef, register_builtin_skill

_WRITE_PROMPT = """\
You are an expert executive author and technical writer.

## Task
$ARGUMENTS

## Execution Protocol
1. Analyze audience, domain context, required depth, and tone.
2. Outline the document with logical headings, sub-headings, tables, and callout blocks.
3. If publication-grade Word/PDF export is requested, invoke `document_creator(title=..., subtitle=..., content=..., format="docx")`.
4. Otherwise, write the markdown artifact using `file_write(file_path=..., content=...)`.
5. Return the finalized content and file location.
"""

_EXECUTIVE_DOC_PROMPT = """\
Create an executive publication-grade Word (.docx) or PDF document.

## Document Topic
$ARGUMENTS

## Execution Protocol
1. Structure the document with:
   - Executive Summary
   - Problem Statement & Objectives
   - Core Architectural / Strategic Framework
   - Comparative Tables and Benchmark Metrics
   - Actionable Implementation Roadmap
2. Use `document_creator` with parameters:
   - `title`: Main Document Title
   - `subtitle`: Subtitle description
   - `author`: "BR JARVIS AI"
   - `content`: Formatted Markdown content with headings, tables, callout blocks
   - `format`: `"docx"` (or `"pdf"`)
   - `auto_open`: `True`
3. Return the generated file path and document summary.
"""

_EMAIL_DRAFT_PROMPT = """\
Draft and optionally dispatch a high-impact professional email.

## Email Intent
$ARGUMENTS

## Format
- **Subject Line**: Direct, high-clarity, action-oriented.
- **Greeting**: Professional and tailored.
- **Core Message**: 2-4 concise paragraphs with clear value or ask.
- **Call-to-Action / Next Steps**: Concrete deliverables and deadlines.
- **Sign-off**: Professional signature.

## Tools
- Use `send_email` or `gmail_send` if immediate dispatch is requested.
- Use `schedule_email` if a specific delivery time is specified.
"""

_BLOG_PROMPT = """\
Create an engaging, SEO-optimized technical blog article.

## Topic
$ARGUMENTS

## Structure
1. **Headline**: Compelling, keyword-rich title.
2. **Hook**: Punchy opening problem statement.
3. **Core Sections**: H2/H3 headings with deep code snippets or concrete architecture patterns.
4. **Key Takeaways & Conclusion**: Bulleted summary and next steps.
5. Save output via `file_write` to workspace or docs directory.
"""

_TRANSLATE_PROMPT = """\
Translate text accurately while preserving technical terminology and tone.

## Translation Task
$ARGUMENTS

## Protocol
1. Identify source and target languages.
2. Preserve markdown syntax, code blocks, technical symbols, and formatting.
3. Output clean translation side-by-side or as target deliverable.
"""

_SUMMARIZE_PROMPT = """\
Generate an executive briefing and digest of documents or transcripts.

## Input Content
$ARGUMENTS

## Protocol
1. Read input files via `file_read` or analyze passed text.
2. Extract the Top 5 Strategic Points, Critical Decisions, and Action Items.
3. Format as a clean markdown brief.
"""


def _register_writer_builtins() -> None:
    register_builtin_skill(
        SkillDef(
            name="write",
            description="Author comprehensive articles, documentation, or publications",
            triggers=["/write", "/author", "write article", "draft document"],
            tools=["document_creator", "create_word_document", "create_pdf_document", "file_write"],
            prompt=_WRITE_PROMPT,
            file_path="builtin:write",
            category="productivity",
            domain="Content Authoring",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="executive_doc",
            description="Generate publication-grade Word (.docx) or PDF executive report",
            triggers=["/doc", "/word-doc", "/pdf-report", "create docx", "generate report document"],
            tools=["document_creator", "create_word_document", "create_pdf_document", "open_app"],
            prompt=_EXECUTIVE_DOC_PROMPT,
            file_path="builtin:executive_doc",
            category="productivity",
            domain="Document Generation",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="email_draft",
            description="Draft, polish, or send high-impact professional emails",
            triggers=["/draft-email", "/send-email", "draft email", "compose email"],
            tools=["send_email", "gmail_send", "schedule_email"],
            prompt=_EMAIL_DRAFT_PROMPT,
            file_path="builtin:email_draft",
            category="productivity",
            domain="Email Communication",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="blog_post",
            description="Write SEO-optimized technical blog posts and tutorials",
            triggers=["/blog", "/article", "write blog post"],
            tools=["file_write", "document_creator"],
            prompt=_BLOG_PROMPT,
            file_path="builtin:blog_post",
            category="marketing",
            domain="Content Marketing",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="translate",
            description="Accurately translate technical and business documents across languages",
            triggers=["/translate", "translate this"],
            tools=["file_read", "file_write"],
            prompt=_TRANSLATE_PROMPT,
            file_path="builtin:translate",
            category="general",
            domain="Translation",
            user_invocable=True,
            source="builtin",
        )
    )

    register_builtin_skill(
        SkillDef(
            name="summarize",
            description="Produce executive summaries and action items from text or files",
            triggers=["/summarize", "/tldr", "summarize this document", "executive summary"],
            tools=["file_read", "file_list"],
            prompt=_SUMMARIZE_PROMPT,
            file_path="builtin:summarize",
            category="productivity",
            domain="Summarization",
            user_invocable=True,
            source="builtin",
        )
    )


_register_writer_builtins()
