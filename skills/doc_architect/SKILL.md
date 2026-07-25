---
name: doc_architect
description: Autonomous documentation architect and Mermaid diagram authoring engine.
user_invocable: true
---

# 🎨 Autonomous Documentation Architect Skill

When the user asks to generate project documentation, visual diagrams, or architecture walkthroughs:

## Execution Steps:
1. **Workspace Structure Analysis**: Use `file_list` and `file_search_semantic` to inspect package layouts.
2. **Mermaid Flow Diagram Generation**: Create Mermaid `graph TD` or `sequenceDiagram` flowcharts illustrating component relationships.
3. **Structured Technical Spec**: Render clear GitHub Flavored Markdown with alerts (`> [!NOTE]`, `> [!IMPORTANT]`).
4. **Walkthrough Export**: Save the generated documentation to the brain artifacts directory.
