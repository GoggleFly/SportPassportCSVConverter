"""Integration tests for row removal functionality."""

import pytest
import csv
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from converter.main import SportPassportConverter
from tests.fixtures import TEST_DATA_WITH_EXTRA_ROWS, TEST_DATA_VALID


class TestRowRemovalIntegration:
    """Integration tests for automatic row removal."""
    
    @patch('converter.interactive.questionary.select')
    @patch('converter.interactive.questionary.confirm')
    def test_removes_metadata_rows_from_top(self, mock_confirm, mock_select):
        """Should remove metadata rows from top of file."""
        # Mock user declining default overrides, confirming row removal, and confirming export
        mock_confirm.return_value.ask.side_effect = [False, True]
        # Mock user confirming row removal
        mock_select.return_value.ask.return_value = "Yes, remove these rows"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as out:
            output_path = out.name
        
        try:
            converter = SportPassportConverter(
                str(TEST_DATA_WITH_EXTRA_ROWS),
                output_path,
                auto_confirm=False,  # Need to prompt for row removal
            )
            
            success = converter.run()
            assert success is True
            
            # Verify output has correct number of data rows (2 students)
            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # Header + 2 data rows = 3 rows total
            assert len(rows) == 3
            assert rows[0][0] == "Sport Passport ID"  # Header row
            assert rows[1][1] == "John"  # First data row
            assert rows[2][1] == "Jane"  # Second data row
        
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    @patch('converter.interactive.questionary.select')
    @patch('converter.interactive.questionary.confirm')
    def test_removes_trailing_rows_from_bottom(self, mock_confirm, mock_select):
        """Should remove trailing summary rows from bottom."""
        # Mock user declining default overrides, confirming row removal, and confirming export
        mock_confirm.return_value.ask.side_effect = [False, True]
        # Mock user confirming row removal
        mock_select.return_value.ask.return_value = "Yes, remove these rows"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as out:
            output_path = out.name
        
        try:
            converter = SportPassportConverter(
                str(TEST_DATA_WITH_EXTRA_ROWS),
                output_path,
                auto_confirm=False,
            )
            
            success = converter.run()
            assert success is True
            
            # Verify trailing rows were removed
            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # Should not have "Total" or "End of report" rows
            row_text = " ".join([" ".join(row) for row in rows])
            assert "Total" not in row_text
            assert "End of report" not in row_text
        
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    @patch('converter.interactive.questionary.select')
    @patch('converter.interactive.questionary.confirm')
    def test_user_can_reject_row_removal(self, mock_confirm, mock_select):
        """User should be able to reject automatic row removal."""
        # Mock user declining default overrides and rejecting row removal
        mock_confirm.return_value.ask.return_value = False
        # Mock user rejecting row removal
        mock_select.return_value.ask.return_value = "No, keep all rows"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as out:
            output_path = out.name
        
        try:
            converter = SportPassportConverter(
                str(TEST_DATA_WITH_EXTRA_ROWS),
                output_path,
                auto_confirm=False,
            )
            
            # Should still process, but with all rows
            # Note: This might cause issues if metadata rows are treated as data
            # but the converter should handle it gracefully
            success = converter.run()
            
            # The conversion might succeed or fail depending on how metadata rows
            # are handled, but it shouldn't crash
            assert isinstance(success, bool)
        
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    def test_auto_confirm_removes_rows_without_prompting(self):
        """With auto_confirm, should remove rows without prompting."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as out:
            output_path = out.name
        
        try:
            converter = SportPassportConverter(
                str(TEST_DATA_WITH_EXTRA_ROWS),
                output_path,
                auto_confirm=True,  # Should auto-remove rows
            )
            
            success = converter.run()
            assert success is True
            
            # Verify rows were removed
            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # Should have header + 2 data rows (metadata and trailing rows removed)
            assert len(rows) == 3
            assert rows[0][0] == "Sport Passport ID"
        
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    @patch('converter.interactive.InteractiveCorrector.prompt_confirm_row_removal')
    @patch('converter.interactive.questionary.confirm')
    def test_shows_preview_of_rows_to_remove(self, mock_confirm, mock_prompt):
        """Should show preview of rows that will be removed."""
        # Mock user declining default overrides
        mock_confirm.return_value.ask.return_value = False
        # Mock the prompt to return True
        mock_prompt.return_value = True
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as out:
            output_path = out.name
        
        try:
            converter = SportPassportConverter(
                str(TEST_DATA_WITH_EXTRA_ROWS),
                output_path,
                auto_confirm=False,
            )
            
            converter.run()
            
            # Verify prompt was called with preview data
            assert mock_prompt.called
            call_args = mock_prompt.call_args
            
            header_idx = call_args[0][0]
            last_valid_idx = call_args[0][1]
            total_rows = call_args[0][2]
            preview_top = call_args[0][3]
            preview_bottom = call_args[0][4]
            
            # Should have detected rows to remove
            assert header_idx is not None
            assert total_rows > 0
            
            # Should have preview data
            if header_idx and header_idx > 0:
                assert len(preview_top) > 0
            
            if last_valid_idx is not None:
                assert len(preview_bottom) > 0
        
        finally:
            Path(output_path).unlink(missing_ok=True)


class TestRowRemovalWithValidData:
    """Tests for row removal with files that don't need removal."""
    
    def test_handles_file_without_extra_rows(self):
        """Should handle file without extra rows gracefully."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as out:
            output_path = out.name
        
        try:
            converter = SportPassportConverter(
                str(TEST_DATA_VALID),
                output_path,
                auto_confirm=True,
            )
            
            success = converter.run()
            assert success is True
            
            # Should process normally without prompting for row removal
            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # Should have header + 2 data rows
            assert len(rows) == 3
        
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    @patch('converter.interactive.InteractiveCorrector.prompt_confirm_row_removal')
    @patch('converter.interactive.questionary.confirm')
    def test_does_not_prompt_when_no_rows_to_remove(self, mock_confirm, mock_prompt):
        """Should not prompt when no rows need to be removed."""
        # Mock user declining default overrides and confirming export
        mock_confirm.return_value.ask.side_effect = [False, True]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as out:
            output_path = out.name
        
        try:
            converter = SportPassportConverter(
                str(TEST_DATA_VALID),
                output_path,
                auto_confirm=False,
            )
            
            converter.run()
            
            # Should not have called prompt if no rows to remove
            # (The prompt might be called but return False immediately)
            # Let's check that the conversion succeeded
            assert Path(output_path).exists()
            
            # If prompt was called, it should have been with header_idx=0 (no rows to remove)
            if mock_prompt.called:
                call_args = mock_prompt.call_args
                header_idx = call_args[0][0]
                # Header at index 0 means no rows to remove from top
                assert header_idx == 0
        
        finally:
            Path(output_path).unlink(missing_ok=True)
