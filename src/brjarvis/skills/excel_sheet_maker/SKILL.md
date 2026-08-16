---
name: excel_sheet_maker
description: Automated Excel spreadsheet creation and codebase architectural analysis skill.
---

# 📊 Skill: Excel Sheet Maker & Codebase Analysis

Use this skill whenever the user requests:
- Creating Excel spreadsheets (`.xlsx`)
- Exporting tables, datasets, or logs to Excel
- Analyzing the JARVIS codebase into a spreadsheet (`JARVIS_Project_Full_Analysis.xlsx`)

## Workflow:

1. **For Project Full Analysis Requests**:
   - Call `analyze_project_to_excel` with `project_path="."`.
   - Returns a multi-tab formatted workbook containing Executive Summary, File Inventory Matrix (sorted by LOC), and Subsystem Breakdown.

2. **For Custom Spreadsheet Creation**:
   - Call `create_excel_sheet` passing:
     - `title`: Sheet name
     - `headers`: List of column headers
     - `rows`: List of data rows
     - `filename`: Output filename ending in `.xlsx`
     - `auto_open`: True to launch Excel on completion.
