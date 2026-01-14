"""Tests for interactive executable functionality."""

import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Import the interactive executable functions
# We need to import them dynamically since they're in a script file
import importlib.util
spec = importlib.util.spec_from_file_location(
    "converter_interactive",
    Path(__file__).parent.parent / "converter_interactive.py"
)
converter_interactive = importlib.util.module_from_spec(spec)
sys.modules["converter_interactive"] = converter_interactive
spec.loader.exec_module(converter_interactive)


class TestGetInputFile:
    """Tests for get_input_file() function."""
    
    @pytest.fixture
    def temp_csv_file(self, tmp_path):
        """Create a temporary CSV file for testing."""
        test_file = tmp_path / "test_input.csv"
        test_file.write_text("Header1,Header2\nValue1,Value2\n")
        return test_file
    
    @pytest.fixture
    def temp_xlsx_file(self, tmp_path):
        """Create a temporary XLSX file for testing."""
        test_file = tmp_path / "test_input.xlsx"
        # Create a minimal valid XLSX file (just create the path for now)
        # In real tests, we'd use a test fixture XLSX file
        test_file.write_text("dummy")  # Placeholder
        return test_file
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_input_file_valid_path(self, mock_print, mock_input, temp_csv_file):
        """Should accept a valid file path."""
        mock_input.return_value = str(temp_csv_file)
        
        result = converter_interactive.get_input_file()
        
        assert result == temp_csv_file.resolve()
        assert result.exists()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_input_file_quoted_double_quotes(self, mock_print, mock_input, temp_csv_file):
        """Should handle double-quoted paths."""
        mock_input.return_value = f'"{temp_csv_file}"'
        
        result = converter_interactive.get_input_file()
        
        assert result == temp_csv_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_input_file_quoted_single_quotes(self, mock_print, mock_input, temp_csv_file):
        """Should handle single-quoted paths."""
        mock_input.return_value = f"'{temp_csv_file}'"
        
        result = converter_interactive.get_input_file()
        
        assert result == temp_csv_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_input_file_empty_path_retries(self, mock_print, mock_input, temp_csv_file):
        """Should retry when empty path is entered."""
        mock_input.side_effect = ["", str(temp_csv_file)]
        
        result = converter_interactive.get_input_file()
        
        assert result == temp_csv_file.resolve()
        # Should have called input twice (empty, then valid)
        assert mock_input.call_count == 2
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_input_file_nonexistent_file_retries(self, mock_print, mock_input, tmp_path):
        """Should retry when file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.csv"
        test_file = tmp_path / "test.csv"
        test_file.write_text("Header\nValue\n")
        
        mock_input.side_effect = [str(nonexistent), "y", str(test_file)]
        
        result = converter_interactive.get_input_file()
        
        assert result == test_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_input_file_nonexistent_file_exits(self, mock_print, mock_input, tmp_path):
        """Should exit when user declines to retry."""
        nonexistent = tmp_path / "nonexistent.csv"
        
        mock_input.side_effect = [str(nonexistent), "n"]
        
        with pytest.raises(SystemExit) as exc_info:
            converter_interactive.get_input_file()
        
        assert exc_info.value.code == 1
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_input_file_directory_not_file(self, mock_print, mock_input, tmp_path):
        """Should reject directories."""
        # tmp_path is a directory
        test_file = tmp_path / "test.csv"
        test_file.write_text("Header\nValue\n")
        
        mock_input.side_effect = [str(tmp_path), "y", str(test_file)]
        
        result = converter_interactive.get_input_file()
        
        assert result == test_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_input_file_invalid_extension(self, mock_print, mock_input, tmp_path):
        """Should reject files with unsupported extensions."""
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("test content")
        valid_file = tmp_path / "test.csv"
        valid_file.write_text("Header\nValue\n")
        
        mock_input.side_effect = [str(invalid_file), "y", str(valid_file)]
        
        result = converter_interactive.get_input_file()
        
        assert result == valid_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_input_file_expands_tilde(self, mock_print, mock_input, tmp_path, monkeypatch):
        """Should expand ~ to home directory."""
        # Mock home directory
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))
        
        test_file = home_dir / "test.csv"
        test_file.write_text("Header\nValue\n")
        
        mock_input.return_value = "~/test.csv"
        
        result = converter_interactive.get_input_file()
        
        assert result.exists()
        assert "test.csv" in str(result)
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_input_file_relative_path(self, mock_print, mock_input, tmp_path, monkeypatch):
        """Should resolve relative paths."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("Header\nValue\n")
        
        # Change to tmp_path directory
        original_cwd = Path.cwd()
        monkeypatch.chdir(tmp_path)
        
        try:
            mock_input.return_value = "test.csv"
            
            result = converter_interactive.get_input_file()
            
            assert result == test_file.resolve()
        finally:
            monkeypatch.chdir(original_cwd)


class TestGetOutputFile:
    """Tests for get_output_file() function."""
    
    @pytest.fixture
    def input_file(self, tmp_path):
        """Create a sample input file."""
        test_file = tmp_path / "input.xlsx"
        test_file.write_text("dummy")
        return test_file
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_output_file_uses_default(self, mock_print, mock_input, input_file):
        """Should use default output name when Enter is pressed."""
        mock_input.return_value = ""
        
        result = converter_interactive.get_output_file(input_file)
        
        expected = input_file.with_suffix('.converted.csv')
        assert result == expected.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_output_file_custom_path(self, mock_print, mock_input, input_file, tmp_path):
        """Should accept custom output path."""
        custom_output = tmp_path / "custom_output.csv"
        mock_input.return_value = str(custom_output)
        
        result = converter_interactive.get_output_file(input_file)
        
        assert result == custom_output.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_output_file_adds_csv_extension(self, mock_print, mock_input, input_file, tmp_path):
        """Should add .csv extension if missing."""
        custom_output = tmp_path / "output"
        mock_input.return_value = str(custom_output)
        
        result = converter_interactive.get_output_file(input_file)
        
        assert result.suffix == '.csv'
        assert result.stem == 'output'
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_output_file_creates_directory(self, mock_print, mock_input, input_file, tmp_path):
        """Should create output directory if it doesn't exist."""
        new_dir = tmp_path / "new_directory"
        output_file = new_dir / "output.csv"
        
        mock_input.side_effect = [str(output_file), "y"]  # Create directory
        
        result = converter_interactive.get_output_file(input_file)
        
        assert new_dir.exists()
        assert result == output_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_output_file_directory_creation_declined(self, mock_print, mock_input, input_file, tmp_path):
        """Should retry when directory creation is declined."""
        new_dir = tmp_path / "new_directory"
        output_file = new_dir / "output.csv"
        fallback_output = tmp_path / "fallback.csv"
        
        mock_input.side_effect = [
            str(output_file),  # First attempt - directory doesn't exist
            "n",  # Decline to create
            str(fallback_output),  # Provide different path
        ]
        
        result = converter_interactive.get_output_file(input_file)
        
        assert not new_dir.exists()
        assert result == fallback_output.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_output_file_overwrite_existing(self, mock_print, mock_input, input_file, tmp_path):
        """Should ask to overwrite existing file."""
        existing_file = tmp_path / "existing.csv"
        existing_file.write_text("existing content")
        
        mock_input.side_effect = [str(existing_file), "y"]  # Confirm overwrite
        
        result = converter_interactive.get_output_file(input_file)
        
        assert result == existing_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_output_file_overwrite_declined(self, mock_print, mock_input, input_file, tmp_path):
        """Should retry when overwrite is declined."""
        existing_file = tmp_path / "existing.csv"
        existing_file.write_text("existing content")
        new_file = tmp_path / "new_file.csv"
        
        mock_input.side_effect = [
            str(existing_file),  # First attempt - file exists
            "n",  # Decline overwrite
            str(new_file),  # Provide different path
        ]
        
        result = converter_interactive.get_output_file(input_file)
        
        assert result == new_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_output_file_quoted_path(self, mock_print, mock_input, input_file, tmp_path):
        """Should handle quoted output paths."""
        output_file = tmp_path / "output.csv"
        
        mock_input.return_value = f'"{output_file}"'
        
        result = converter_interactive.get_output_file(input_file)
        
        assert result == output_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_get_output_file_expands_tilde(self, mock_print, mock_input, input_file, tmp_path, monkeypatch):
        """Should expand ~ in output path."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))
        
        output_file = home_dir / "output.csv"
        mock_input.return_value = "~/output.csv"
        
        result = converter_interactive.get_output_file(input_file)
        
        assert result.exists() or result.parent.exists()
        assert "output.csv" in str(result)


class TestMainFunction:
    """Tests for main() function integration."""
    
    @pytest.fixture
    def sample_csv_file(self, tmp_path):
        """Create a minimal valid CSV file."""
        csv_file = tmp_path / "input.csv"
        csv_file.write_text(
            "First Name*,Surname*,Gender*,DateOfBirth*,Postcode*,Email*,ClassifiedAsDisabled*\n"
            "John,Smith,Male,16/12/2001,SW1A 1AA,john@example.com,No\n"
        )
        return csv_file
    
    @patch('converter_interactive.get_output_file')
    @patch('converter_interactive.get_input_file')
    @patch('converter_interactive.SportPassportConverter')
    @patch('builtins.print')
    def test_main_successful_conversion(
        self,
        mock_print,
        mock_converter_class,
        mock_get_input,
        mock_get_output,
        sample_csv_file,
        tmp_path
    ):
        """Should run conversion successfully."""
        output_file = tmp_path / "output.csv"
        mock_get_input.return_value = sample_csv_file
        mock_get_output.return_value = output_file
        
        # Mock successful converter run
        mock_converter = MagicMock()
        mock_converter.run.return_value = True
        mock_converter_class.return_value = mock_converter
        
        with pytest.raises(SystemExit) as exc_info:
            converter_interactive.main()
        
        assert exc_info.value.code == 0
        mock_converter_class.assert_called_once_with(
            str(sample_csv_file),
            str(output_file),
            auto_confirm=False,
        )
        mock_converter.run.assert_called_once()
    
    @patch('converter_interactive.get_output_file')
    @patch('converter_interactive.get_input_file')
    @patch('converter_interactive.SportPassportConverter')
    @patch('builtins.print')
    def test_main_failed_conversion(
        self,
        mock_print,
        mock_converter_class,
        mock_get_input,
        mock_get_output,
        sample_csv_file,
        tmp_path
    ):
        """Should exit with error code when conversion fails."""
        output_file = tmp_path / "output.csv"
        mock_get_input.return_value = sample_csv_file
        mock_get_output.return_value = output_file
        
        # Mock failed converter run
        mock_converter = MagicMock()
        mock_converter.run.return_value = False
        mock_converter_class.return_value = mock_converter
        
        with pytest.raises(SystemExit) as exc_info:
            converter_interactive.main()
        
        assert exc_info.value.code == 1
    
    @patch('converter_interactive.get_output_file')
    @patch('converter_interactive.get_input_file')
    @patch('builtins.print')
    def test_main_keyboard_interrupt(
        self,
        mock_print,
        mock_get_input,
        mock_get_output,
        sample_csv_file,
        tmp_path
    ):
        """Should handle KeyboardInterrupt gracefully."""
        output_file = tmp_path / "output.csv"
        mock_get_input.return_value = sample_csv_file
        mock_get_output.return_value = output_file
        mock_get_input.side_effect = KeyboardInterrupt()
        
        with pytest.raises(SystemExit) as exc_info:
            converter_interactive.main()
        
        assert exc_info.value.code == 1
    
    @patch('converter_interactive.get_output_file')
    @patch('converter_interactive.get_input_file')
    @patch('builtins.print')
    def test_main_unexpected_exception(
        self,
        mock_print,
        mock_get_input,
        mock_get_output,
        sample_csv_file,
        tmp_path
    ):
        """Should handle unexpected exceptions."""
        output_file = tmp_path / "output.csv"
        mock_get_input.return_value = sample_csv_file
        mock_get_output.return_value = output_file
        mock_get_input.side_effect = ValueError("Unexpected error")
        
        with pytest.raises(SystemExit) as exc_info:
            converter_interactive.main()
        
        assert exc_info.value.code == 1


class TestPathHandlingEdgeCases:
    """Tests for edge cases in path handling."""
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_input_file_path_with_spaces(self, mock_print, mock_input, tmp_path):
        """Should handle file paths with spaces."""
        test_file = tmp_path / "file with spaces.csv"
        test_file.write_text("Header\nValue\n")
        
        mock_input.return_value = str(test_file)
        
        result = converter_interactive.get_input_file()
        
        assert result == test_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_output_file_path_with_spaces(self, mock_print, mock_input, tmp_path):
        """Should handle output paths with spaces."""
        input_file = tmp_path / "input.xlsx"
        input_file.write_text("dummy")
        
        output_file = tmp_path / "output with spaces.csv"
        mock_input.return_value = str(output_file)
        
        result = converter_interactive.get_output_file(input_file)
        
        assert result == output_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_input_file_case_insensitive_extension(self, mock_print, mock_input, tmp_path):
        """Should accept file extensions in different cases."""
        test_file = tmp_path / "test.CSV"
        test_file.write_text("Header\nValue\n")
        
        mock_input.return_value = str(test_file)
        
        result = converter_interactive.get_input_file()
        
        assert result == test_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_output_file_preserves_case_but_ensures_csv(self, mock_print, mock_input, tmp_path):
        """Should ensure .csv extension regardless of input case."""
        input_file = tmp_path / "input.xlsx"
        input_file.write_text("dummy")
        
        # User provides .CSV in uppercase
        output_file = tmp_path / "output.CSV"
        mock_input.return_value = str(output_file)
        
        result = converter_interactive.get_output_file(input_file)
        
        # Should still have .csv extension (lowercase normalized)
        assert result.suffix == '.csv'
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_input_file_quoted_path_with_spaces(self, mock_print, mock_input, tmp_path):
        """Should handle quoted file paths with spaces."""
        test_file = tmp_path / "file with spaces.csv"
        test_file.write_text("Header\nValue\n")
        
        # Test with double quotes
        mock_input.return_value = f'"{test_file}"'
        result = converter_interactive.get_input_file()
        assert result == test_file.resolve()
        
        # Test with single quotes
        mock_input.return_value = f"'{test_file}'"
        result = converter_interactive.get_input_file()
        assert result == test_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_input_file_trailing_whitespace_after_extension(self, mock_print, mock_input, tmp_path):
        """Should trim trailing whitespace after file extension."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("Header\nValue\n")
        
        # Test with trailing space
        mock_input.return_value = f"{test_file} "
        result = converter_interactive.get_input_file()
        assert result == test_file.resolve()
        
        # Test with trailing spaces
        mock_input.return_value = f"{test_file}   "
        result = converter_interactive.get_input_file()
        assert result == test_file.resolve()
        
        # Test with space before extension - should clean to normal extension
        # Create a file with normal name
        test_file2 = tmp_path / "test.csv"
        test_file2.write_text("Header\nValue\n")
        # User enters path with space before extension
        mock_input.return_value = str(tmp_path / "test .csv")
        result = converter_interactive.get_input_file()
        # Should resolve to the cleaned path (test.csv)
        assert result == test_file2.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_output_file_quoted_path_with_spaces(self, mock_print, mock_input, tmp_path):
        """Should handle quoted output paths with spaces."""
        input_file = tmp_path / "input.xlsx"
        input_file.write_text("dummy")
        
        output_file = tmp_path / "output with spaces.csv"
        
        # Test with double quotes
        mock_input.return_value = f'"{output_file}"'
        result = converter_interactive.get_output_file(input_file)
        assert result == output_file.resolve()
        
        # Test with single quotes
        mock_input.return_value = f"'{output_file}'"
        result = converter_interactive.get_output_file(input_file)
        assert result == output_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_output_file_trailing_whitespace_after_extension(self, mock_print, mock_input, tmp_path):
        """Should trim trailing whitespace after file extension in output path."""
        input_file = tmp_path / "input.xlsx"
        input_file.write_text("dummy")
        
        output_file = tmp_path / "output.csv"
        
        # Test with trailing space
        mock_input.return_value = f"{output_file} "
        result = converter_interactive.get_output_file(input_file)
        assert result == output_file.resolve()
        
        # Test with trailing spaces
        mock_input.return_value = f"{output_file}   "
        result = converter_interactive.get_output_file(input_file)
        assert result == output_file.resolve()
        
        # Test quoted path with trailing space
        mock_input.return_value = f'"{output_file} "'
        result = converter_interactive.get_output_file(input_file)
        assert result == output_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_input_file_backslash_escaped_spaces(self, mock_print, mock_input, tmp_path):
        """Should handle backslash-escaped spaces from macOS drag-and-drop."""
        # Create a file with spaces in the name (simulating macOS drag-and-drop)
        test_file = tmp_path / "file with spaces.csv"
        test_file.write_text("Header\nValue\n")
        
        # Simulate macOS drag-and-drop: backslash-escaped spaces
        # The path as it appears when dragged from Finder
        escaped_path = str(test_file).replace(' ', r'\ ')
        mock_input.return_value = escaped_path
        
        result = converter_interactive.get_input_file()
        
        # Should correctly parse and resolve to the actual file
        assert result == test_file.resolve()
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_output_file_backslash_escaped_spaces(self, mock_print, mock_input, tmp_path):
        """Should handle backslash-escaped spaces in output paths."""
        input_file = tmp_path / "input.xlsx"
        input_file.write_text("dummy")
        
        output_file = tmp_path / "output with spaces.csv"
        
        # Simulate macOS drag-and-drop: backslash-escaped spaces
        escaped_path = str(output_file).replace(' ', r'\ ')
        mock_input.return_value = escaped_path
        
        result = converter_interactive.get_output_file(input_file)
        
        # Should correctly parse and resolve to the expected output path
        assert result == output_file.resolve()