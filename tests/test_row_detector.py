"""Tests for row detection functionality."""

import pytest
import pandas as pd
from pathlib import Path

from converter.row_detector import (
    detect_header_row,
    detect_trailing_rows,
    detect_rows_to_remove,
)
from tests.fixtures import TEST_DATA_VALID


class TestHeaderRowDetection:
    """Tests for header row detection."""
    
    def test_detects_header_row_in_dataframe(self):
        """Should detect header row in DataFrame."""
        # Create DataFrame with metadata rows at top
        data = [
            ["School Information", "", "", "", ""],
            ["Generated on 2024-01-01", "", "", "", ""],
            ["First Name*", "Surname*", "Gender*", "DateOfBirth*", "Email*"],
            ["John", "Smith", "Male", "16/12/2001", "john@example.com"],
            ["Jane", "Doe", "Female", "25/12/2001", "jane@example.com"],
        ]
        df = pd.DataFrame(data)
        
        header_idx = detect_header_row(df)
        
        assert header_idx == 2  # Third row (0-indexed) is the header
    
    def test_detects_header_row_in_list(self):
        """Should detect header row in list of rows."""
        rows = [
            ["School Information", "", "", ""],
            ["First Name*", "Surname*", "Gender*", "Email*"],
            ["John", "Smith", "Male", "john@example.com"],
        ]
        
        header_idx = detect_header_row(rows)
        
        assert header_idx == 1  # Second row is the header
    
    def test_handles_no_metadata_rows(self):
        """Should return 0 if first row is already the header."""
        rows = [
            ["First Name*", "Surname*", "Gender*"],
            ["John", "Smith", "Male"],
        ]
        
        header_idx = detect_header_row(rows)
        
        assert header_idx == 0  # First row is the header
    
    def test_requires_minimum_matches(self):
        """Should require minimum number of header matches."""
        rows = [
            ["Some", "Random", "Text"],
            ["First Name*", "Surname*", "Gender*", "DateOfBirth*", "Email*"],
            ["John", "Smith", "Male", "16/12/2001", "john@example.com"],
        ]
        
        header_idx = detect_header_row(rows, min_matches=3)
        
        assert header_idx == 1  # Second row matches enough headers
    
    def test_falls_back_to_pattern_matching(self):
        """Should use pattern matching if header detection fails."""
        # Create rows where header detection might fail but pattern matching works
        rows = [
            ["Metadata", "Row", "Here"],
            ["First Name", "Last Name", "Gender", "DOB", "Email Address"],
            ["John", "Smith", "Male", "16/12/2001", "john@example.com"],
        ]
        
        header_idx = detect_header_row(rows)
        
        # Should find the row that looks like headers
        assert header_idx is not None
        assert header_idx >= 0


class TestTrailingRowDetection:
    """Tests for trailing row detection."""
    
    def test_detects_trailing_empty_rows(self):
        """Should detect and remove trailing empty rows."""
        rows = [
            ["First Name*", "Surname*", "Gender*"],
            ["John", "Smith", "Male"],
            ["Jane", "Doe", "Female"],
            ["", "", ""],
            ["", "", ""],
        ]
        
        last_valid = detect_trailing_rows(rows, header_row_idx=0)
        
        assert last_valid == 2  # Last valid row is index 2
    
    def test_detects_summary_rows(self):
        """Should detect summary rows at the bottom."""
        rows = [
            ["First Name*", "Surname*", "Gender*"],
            ["John", "Smith", "Male"],
            ["Jane", "Doe", "Female"],
            ["Total", "2", "students"],
            ["End of report", "", ""],
        ]
        
        last_valid = detect_trailing_rows(rows, header_row_idx=0)
        
        assert last_valid == 2  # Last valid data row is index 2
    
    def test_handles_no_trailing_rows(self):
        """Should return None if no trailing rows to remove."""
        rows = [
            ["First Name*", "Surname*", "Gender*"],
            ["John", "Smith", "Male"],
            ["Jane", "Doe", "Female"],
        ]
        
        last_valid = detect_trailing_rows(rows, header_row_idx=0)
        
        assert last_valid is None  # No trailing rows to remove
    
    def test_handles_mixed_trailing_content(self):
        """Should handle mix of empty and summary rows."""
        rows = [
            ["First Name*", "Surname*"],
            ["John", "Smith"],
            ["Jane", "Doe"],
            ["", ""],
            ["Total", "2"],
            ["", ""],
        ]
        
        last_valid = detect_trailing_rows(rows, header_row_idx=0)
        
        assert last_valid == 2  # Last valid data row


class TestCombinedRowDetection:
    """Tests for combined row detection."""
    
    def test_detects_both_top_and_bottom_rows(self):
        """Should detect rows to remove from both top and bottom."""
        rows = [
            ["School Information", "", ""],
            ["Metadata", "Row", "Here"],
            ["First Name*", "Surname*", "Gender*"],
            ["John", "Smith", "Male"],
            ["Jane", "Doe", "Female"],
            ["Total", "2", "students"],
            ["", "", ""],
        ]
        
        header_idx, last_valid = detect_rows_to_remove(rows)
        
        assert header_idx == 2  # Header is at index 2
        assert last_valid == 4  # Last valid data row is at index 4
    
    def test_handles_dataframe_input(self):
        """Should work with DataFrame input."""
        data = [
            ["Metadata", "", ""],
            ["First Name*", "Surname*", "Gender*"],
            ["John", "Smith", "Male"],
            ["", "", ""],
        ]
        df = pd.DataFrame(data)
        
        header_idx, last_valid = detect_rows_to_remove(df)
        
        assert header_idx == 1  # Header is at index 1
        assert last_valid == 2  # Last valid row is at index 2


class TestEdgeCases:
    """Tests for edge cases in row detection."""
    
    def test_handles_single_row(self):
        """Should handle file with only header row."""
        rows = [
            ["First Name*", "Surname*", "Gender*"],
        ]
        
        header_idx = detect_header_row(rows)
        last_valid = detect_trailing_rows(rows, header_row_idx=0)
        
        assert header_idx == 0
        assert last_valid is None  # No trailing rows
    
    def test_handles_all_empty_rows(self):
        """Should handle file with only empty rows."""
        rows = [
            ["", "", ""],
            ["", "", ""],
        ]
        
        header_idx = detect_header_row(rows)
        
        # Should return None or 0 (can't really detect header in empty rows)
        assert header_idx is None or header_idx == 0
    
    def test_handles_very_long_metadata(self):
        """Should handle many metadata rows at top."""
        rows = [["Metadata", "Row", str(i)] for i in range(10)]
        rows.append(["First Name*", "Surname*", "Gender*"])
        rows.append(["John", "Smith", "Male"])
        
        header_idx = detect_header_row(rows)
        
        assert header_idx == 10  # Header is after 10 metadata rows
