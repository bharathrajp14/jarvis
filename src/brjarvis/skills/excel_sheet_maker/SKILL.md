---
name: excel_sheet_maker
description: Automated Excel spreadsheet creation, financial model builder, and codebase architectural matrix analyzer.
category: productivity
domain: Spreadsheet & Data Modeling
allowed-tools: [create_excel_sheet, analyze_project_to_excel, file_read, run_code, open_app]
triggers: [/excel, /make-sheet, /excel-analysis, create spreadsheet, analyze project to excel]
user-invocable: true
---

# 📊 Excel Sheet Maker & Codebase Matrix Skill

Use this skill whenever the user requests:
- Creating formatted Excel spreadsheets (`.xlsx`)
- Generating financial models, Gantt schedules, or KPI matrices in Excel
- Analyzing the repository codebase into an Excel workbook (`JARVIS_Project_Full_Analysis.xlsx`)

## Execution Protocol:

1. **For Project Full Analysis Requests**:
   - Call `analyze_project_to_excel(project_path=".")`.
   - Generates a multi-tab formatted workbook containing Executive Summary, File Inventory Matrix (sorted by LOC), and Subsystem Breakdown.

2. **For Custom Spreadsheet Creation**:
   - Call `create_excel_sheet` passing:
     - `title`: Sheet name
     - `headers`: List of column header strings
     - `rows`: 2D list of data rows
     - `filename`: Output filename ending in `.xlsx`
     - `auto_open`: `True` to launch Excel on completion.
3. Confirm file path, total rows written, and summary of metrics.
