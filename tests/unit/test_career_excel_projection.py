# tests/unit/test_career_excel_projection.py — Excel 10-Sheet Projection Unit Tests
import os
import tempfile
import pytest
from pathlib import Path
import openpyxl

from career.spreadsheet.projection import CareerSpreadsheetProjection
from career.spreadsheet.tracker_excel import CareerTrackerWorkbook


def test_10_sheet_excel_projection():
    temp_dir = tempfile.mkdtemp()
    test_excel_path = Path(temp_dir) / "Test_Career_Tracker.xlsx"

    projection = CareerSpreadsheetProjection(workbook_path=test_excel_path)
    res = projection.project_database_to_excel()

    assert res["status"] == "SUCCESS_VERIFIED"
    assert test_excel_path.exists()
    assert test_excel_path.stat().st_size > 0

    # Load and verify 10 sheet names
    wb = openpyxl.load_workbook(test_excel_path, read_only=True)
    sheet_names = wb.sheetnames
    wb.close()

    expected_sheets = [
        "Applications", "Jobs", "Interviews", "Offers", "Followups",
        "Contacts", "Email Events", "Resume Versions", "Analytics", "Settings"
    ]
    for s in expected_sheets:
        assert s in sheet_names, f"Expected sheet '{s}' missing from generated Excel workbook."


def test_excel_concurrency_lock_handling():
    temp_dir = tempfile.mkdtemp()
    test_excel_path = Path(temp_dir) / "Locked_Career_Tracker.xlsx"

    # Create initial file
    projection = CareerSpreadsheetProjection(workbook_path=test_excel_path)
    projection.project_database_to_excel()

    # Verify locked file check doesn't crash
    is_locked = projection.is_file_locked(test_excel_path)
    assert isinstance(is_locked, bool)
