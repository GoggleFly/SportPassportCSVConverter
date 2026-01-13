"""Tests for column name variation matching."""

import pytest
import tempfile
import csv
from pathlib import Path
from unittest.mock import patch

from converter.main import SportPassportConverter
from converter.column_variations import (
    normalize_column_name,
    find_best_match,
    find_column_matches,
    get_field_display_name,
    COLUMN_VARIATIONS,
)
from converter.schema import SPORT_PASSPORT_SCHEMA


class TestColumnNormalization:
    """Tests for column name normalization."""
    
    def test_normalize_removes_asterisks(self):
        """Should remove asterisks from column names."""
        assert normalize_column_name("First Name*") == "first name"
        assert normalize_column_name("Postcode*") == "postcode"
    
    def test_normalize_handles_spaces(self):
        """Should normalize spaces."""
        assert normalize_column_name("First Name") == "first name"
        assert normalize_column_name("First  Name") == "first name"
        assert normalize_column_name("First_Name") == "first name"
        assert normalize_column_name("First-Name") == "first name"
    
    def test_normalize_case_insensitive(self):
        """Should convert to lowercase."""
        assert normalize_column_name("FIRST NAME") == "first name"
        assert normalize_column_name("First Name") == "first name"
        assert normalize_column_name("first name") == "first name"


class TestBestMatch:
    """Tests for finding best matches."""
    
    def test_exact_match_returns_one(self):
        """Exact match should return score of 1.0."""
        score = find_best_match("First Name", "first_name", ["First Name", "FName"])
        assert score == 1.0
    
    def test_partial_match_returns_high_score(self):
        """Partial match should return high score."""
        score = find_best_match("First Name", "first_name", ["First Name*", "FName"])
        assert score >= 0.8
    
    def test_word_overlap_returns_medium_score(self):
        """Word overlap should return medium score."""
        score = find_best_match("Given Name", "first_name", ["First Name", "Given Name"])
        assert score >= 0.5
    
    def test_no_match_returns_low_score(self):
        """No match should return low score."""
        score = find_best_match("Random Column", "first_name", ["First Name", "FName"])
        assert score < 0.5


class TestFindColumnMatches:
    """Tests for finding column matches."""
    
    def test_finds_exact_matches(self):
        """Should find exact matches."""
        headers = ["First Name*", "Surname*", "DateOfBirth*"]
        matches = find_column_matches(headers, min_confidence=0.5)
        
        assert "First Name*" in matches
        assert "Surname*" in matches
        assert "DateOfBirth*" in matches
    
    def test_finds_variation_matches(self):
        """Should find variation matches."""
        headers = ["DOB", "Post Code", "E-mail"]
        matches = find_column_matches(headers, min_confidence=0.5)
        
        # Should match DOB to date_of_birth
        assert "DOB" in matches
        assert matches["DOB"][0] == "date_of_birth"
        
        # Should match Post Code to postcode
        assert "Post Code" in matches
        assert matches["Post Code"][0] == "postcode"
        
        # Should match E-mail to email
        assert "E-mail" in matches
        assert matches["E-mail"][0] == "email"
    
    def test_respects_min_confidence(self):
        """Should only return matches above confidence threshold."""
        headers = ["Random Column", "First Name"]
        matches = find_column_matches(headers, min_confidence=0.8)
        
        # Random Column should not match
        assert "Random Column" not in matches
        # First Name should match
        assert "First Name" in matches
    
    def test_handles_empty_headers(self):
        """Should handle empty headers gracefully."""
        headers = ["", "  ", "First Name"]
        matches = find_column_matches(headers, min_confidence=0.5)
        
        assert "" not in matches
        assert "  " not in matches
        assert "First Name" in matches


class TestColumnVariationIntegration:
    """Integration tests for column variation matching."""
    
    def test_converts_file_with_variation_column_names(self):
        """Should convert file with variation column names."""
        import csv
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as test_file:
            writer = csv.writer(test_file)
            writer.writerow(["First Name*", "Surname*", "DOB", "Post Code", "E-mail", "Gender*", "ClassifiedAsDisabled*", "MedicalConditions", "Address1", "Address2", "PhoneNumber", "TownCity", "County", "Country", "EmergencyContactName", "EmergencyContactPhone", "EmergencyContactPhone2", "SchoolYear", "CourseID", "Sport Passport ID"])
            writer.writerow(["John", "Smith", "16/12/2001", "E1 9BR", "john@example.com", "Male", "No", "", "", "", "", "", "", "England", "", "", "", "9", "101", ""])
            
            output_path = test_file.name.replace('.csv', '_out.csv')
        
        try:
            converter = SportPassportConverter(
                test_file.name,
                output_path,
                auto_confirm=True,  # Auto-confirm variation mappings
            )
            
            success = converter.run()
            assert success is True
            
            # Verify output
            with open(output_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 1
            assert rows[0]["First Name*"] == "John"
            assert rows[0]["Surname*"] == "Smith"
            assert rows[0]["DateOfBirth*"] == "16/12/2001"
            assert rows[0]["Postcode*"] == "E1 9BR"
            assert rows[0]["Email*"] == "john@example.com"
        
        finally:
            Path(test_file.name).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)
    
    @patch('converter.interactive.questionary.select')
    @patch('converter.interactive.questionary.confirm')
    def test_prompts_user_to_confirm_variations(self, mock_confirm, mock_select):
        """Should prompt user to confirm variation mappings."""
        # Mock user declining default overrides, confirming variation mappings, and confirming export
        mock_confirm.return_value.ask.side_effect = [False, True]
        mock_select.return_value.ask.return_value = "Yes, use these mappings"
        
        import csv
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as test_file:
            writer = csv.writer(test_file)
            writer.writerow(["First Name*", "Surname*", "DOB", "Post Code", "E-mail", "Gender*", "ClassifiedAsDisabled*", "MedicalConditions", "Address1", "Address2", "PhoneNumber", "TownCity", "County", "Country", "EmergencyContactName", "EmergencyContactPhone", "EmergencyContactPhone2", "SchoolYear", "CourseID", "Sport Passport ID"])
            writer.writerow(["John", "Smith", "16/12/2001", "E1 9BR", "john@example.com", "Male", "No", "", "", "", "", "", "", "England", "", "", "", "9", "101", ""])
            
            output_path = test_file.name.replace('.csv', '_out.csv')
        
        try:
            converter = SportPassportConverter(
                test_file.name,
                output_path,
                auto_confirm=False,  # Should prompt for variations
            )
            
            success = converter.run()
            assert success is True
            
            # Verify prompt was called
            assert mock_select.called
        
        finally:
            Path(test_file.name).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)
    
    @patch('converter.interactive.questionary.select')
    @patch('converter.interactive.questionary.confirm')
    def test_user_can_reject_variation_mappings(self, mock_confirm, mock_select):
        """User should be able to reject variation mappings."""
        # Mock user declining default overrides and rejecting variation mappings
        mock_confirm.return_value.ask.return_value = False
        mock_select.return_value.ask.return_value = "No, skip variation matching"
        
        import csv
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as test_file:
            writer = csv.writer(test_file)
            writer.writerow(["First Name*", "Surname*", "DOB", "Post Code", "E-mail", "Gender*", "ClassifiedAsDisabled*", "MedicalConditions", "Address1", "Address2", "PhoneNumber", "TownCity", "County", "Country", "EmergencyContactName", "EmergencyContactPhone", "EmergencyContactPhone2", "SchoolYear", "CourseID", "Sport Passport ID"])
            writer.writerow(["John", "Smith", "16/12/2001", "E1 9BR", "john@example.com", "Male", "No", "", "", "", "", "", "", "England", "", "", "", "9", "101", ""])
            
            output_path = test_file.name.replace('.csv', '_out.csv')
        
        try:
            converter = SportPassportConverter(
                test_file.name,
                output_path,
                auto_confirm=False,
            )
            
            # Should fail because mandatory columns are missing (variations rejected)
            result = converter.run()
            assert result is False
        
        finally:
            Path(test_file.name).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)


class TestCommonVariations:
    """Tests for common column name variations."""
    
    def test_date_of_birth_variations(self):
        """Should match common date of birth variations."""
        variations = ["DOB", "Date of Birth", "Birth Date", "DateOfBirth"]
        for var in variations:
            matches = find_column_matches([var], min_confidence=0.5)
            assert var in matches
            assert matches[var][0] == "date_of_birth"
    
    def test_postcode_variations(self):
        """Should match common postcode variations."""
        variations = ["Post Code", "Postal Code", "ZIP Code", "Postcode"]
        for var in variations:
            matches = find_column_matches([var], min_confidence=0.5)
            assert var in matches
            assert matches[var][0] == "postcode"
    
    def test_school_postcode_variations(self):
        """Should match School Postcode variations to postcode field."""
        variations = ["School Postcode", "School Postcode*", "School Post Code", "School Post Code*", "School Postal Code"]
        for var in variations:
            matches = find_column_matches([var], min_confidence=0.5)
            assert var in matches, f"'{var}' should match postcode"
            assert matches[var][0] == "postcode", f"'{var}' should map to postcode field"
    
    def test_email_variations(self):
        """Should match common email variations."""
        variations = ["E-mail", "E-Mail", "Email Address", "Mail"]
        for var in variations:
            matches = find_column_matches([var], min_confidence=0.5)
            assert var in matches
            assert matches[var][0] == "email"
    
    def test_name_variations(self):
        """Should match common name variations."""
        # First name variations
        first_name_vars = ["Given Name", "Forename", "First"]
        for var in first_name_vars:
            matches = find_column_matches([var], min_confidence=0.5)
            assert var in matches
            assert matches[var][0] == "first_name"
        
        # Surname variations
        surname_vars = ["Last Name", "Family Name", "Second Name"]
        for var in surname_vars:
            matches = find_column_matches([var], min_confidence=0.5)
            assert var in matches
            assert matches[var][0] == "surname"


class TestManualColumnMapping:
    """Tests for manual column mapping functionality."""
    
    @patch('converter.interactive.InteractiveCorrector.prompt_for_column_mismatch')
    @patch('converter.interactive.questionary.select')
    @patch('converter.interactive.questionary.confirm')
    def test_manual_column_mapping_success(self, mock_confirm, mock_select, mock_mismatch):
        """Should successfully map unmatched columns manually."""
        # Mock: decline defaults, then confirm export
        mock_confirm.return_value.ask.side_effect = [False, True]
        # Select schema field for manual mapping
        mock_select.return_value.ask.side_effect = [
            "First Name [required]",  # Manual mapping choice
        ]
        # Mock column mismatch - return None (no repair needed)
        mock_mismatch.return_value = None
        
        import csv
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as test_file:
            writer = csv.writer(test_file)
            # Use an unusual column name that definitely won't match (no variation match)
            # Note: Must have exactly 20 columns to match schema
            writer.writerow(["XYZUnknownColumn", "Surname*", "Gender*", "ClassifiedAsDisabled*", "MedicalConditions", "DateOfBirth*", "Address1", "Address2", "PhoneNumber", "TownCity", "County", "Postcode*", "Country", "EmergencyContactName", "EmergencyContactPhone", "EmergencyContactPhone2", "Email*", "SchoolYear", "CourseID", "Sport Passport ID"])
            writer.writerow(["John", "Smith", "Male", "No", "", "16/12/2001", "", "", "", "", "", "E1 9BR", "England", "", "", "", "john@example.com", "9", "101", ""])
            
            output_path = test_file.name.replace('.csv', '_out.csv')
        
        try:
            converter = SportPassportConverter(
                test_file.name,
                output_path,
                auto_confirm=False,
            )
            
            success = converter.run()
            # Should succeed - "XYZUnknownColumn" should be manually mapped to "first_name"
            assert success is True
            
            # Verify manual mapping prompt was called
            assert mock_select.called
        
        finally:
            Path(test_file.name).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)
    
    @patch('converter.interactive.InteractiveCorrector.prompt_for_column_mismatch')
    @patch('converter.interactive.questionary.select')
    @patch('converter.interactive.questionary.confirm')
    def test_manual_column_mapping_skip(self, mock_confirm, mock_select, mock_mismatch):
        """Should allow skipping unmatched columns."""
        # Mock: decline defaults, then confirm export
        mock_confirm.return_value.ask.side_effect = [False, True]
        # Skip the unmatched column
        mock_select.return_value.ask.side_effect = [
            "[dim]Skip this column[/dim]",
        ]
        # Mock column mismatch - return None (no repair needed)
        mock_mismatch.return_value = None
        
        import csv
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as test_file:
            writer = csv.writer(test_file)
            # Use an unusual column name that won't match - make sure we have all required fields
            # Note: Must have exactly 20 columns to match schema
            writer.writerow(["RandomColumn", "First Name*", "Surname*", "Gender*", "ClassifiedAsDisabled*", "MedicalConditions", "DateOfBirth*", "Address1", "Address2", "PhoneNumber", "TownCity", "County", "Postcode*", "Country", "EmergencyContactName", "EmergencyContactPhone", "EmergencyContactPhone2", "Email*", "SchoolYear", "CourseID"])
            writer.writerow(["Ignore", "John", "Smith", "Male", "No", "", "16/12/2001", "", "", "", "", "", "E1 9BR", "England", "", "", "", "john@example.com", "9", "101"])
            
            output_path = test_file.name.replace('.csv', '_out.csv')
        
        try:
            converter = SportPassportConverter(
                test_file.name,
                output_path,
                auto_confirm=False,
            )
            
            success = converter.run()
            # Should succeed - RandomColumn is skipped but all required fields are present
            assert success is True
        
        finally:
            Path(test_file.name).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)
    
    @patch('converter.interactive.InteractiveCorrector.prompt_for_column_mismatch')
    @patch('converter.interactive.questionary.select')
    @patch('converter.interactive.questionary.confirm')
    def test_manual_column_mapping_exit(self, mock_confirm, mock_select, mock_mismatch):
        """Should allow user to exit when unable to match columns."""
        # Mock: decline defaults
        mock_confirm.return_value.ask.return_value = False
        # Exit option selected
        mock_select.return_value.ask.side_effect = [
            "[red]Exit - cannot match this column[/red]",
        ]
        # Mock column mismatch - return None (no repair needed)
        mock_mismatch.return_value = None
        
        import csv
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as test_file:
            writer = csv.writer(test_file)
            # Use an unusual column name that won't match
            # Note: Must have exactly 20 columns to match schema
            writer.writerow(["RandomColumn", "First Name*", "Surname*", "Gender*", "ClassifiedAsDisabled*", "MedicalConditions", "DateOfBirth*", "Address1", "Address2", "PhoneNumber", "TownCity", "County", "Postcode*", "Country", "EmergencyContactName", "EmergencyContactPhone", "EmergencyContactPhone2", "Email*", "SchoolYear", "CourseID"])
            writer.writerow(["Ignore", "John", "Smith", "Male", "No", "", "16/12/2001", "", "", "", "", "", "E1 9BR", "England", "", "", "", "john@example.com", "9", "101"])
            
            output_path = test_file.name.replace('.csv', '_out.csv')
        
        try:
            converter = SportPassportConverter(
                test_file.name,
                output_path,
                auto_confirm=False,
            )
            
            # Should fail/abort when user chooses to exit
            result = converter.run()
            assert result is False
        
        finally:
            Path(test_file.name).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)
    
    @patch('converter.interactive.InteractiveCorrector.prompt_for_column_mismatch')
    @patch('converter.interactive.questionary.select')
    @patch('converter.interactive.questionary.confirm')
    def test_manual_column_mapping_multiple_columns(self, mock_confirm, mock_select, mock_mismatch):
        """Should handle multiple unmatched columns sequentially."""
        # Mock: decline defaults, map multiple columns, confirm export
        mock_confirm.return_value.ask.side_effect = [False, True]  # Decline defaults, confirm export
        # Map first unmatched column to first_name, skip second
        mock_select.return_value.ask.side_effect = [
            "First Name [required]",  # Map first column
            "[dim]Skip this column[/dim]",  # Skip second column
        ]
        # Mock column mismatch - return None (no repair needed)
        mock_mismatch.return_value = None
        
        import csv
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as test_file:
            writer = csv.writer(test_file)
            # Use unusual column names that definitely won't match
            # Note: Must have exactly 20 columns to match schema
            writer.writerow(["XYZUnknownColumn", "RandomColumn123", "Surname*", "Gender*", "ClassifiedAsDisabled*", "MedicalConditions", "DateOfBirth*", "Address1", "Address2", "PhoneNumber", "TownCity", "County", "Postcode*", "Country", "EmergencyContactName", "EmergencyContactPhone", "EmergencyContactPhone2", "Email*", "SchoolYear", "CourseID"])
            writer.writerow(["John", "Ignore", "Smith", "Male", "No", "", "16/12/2001", "", "", "", "", "", "E1 9BR", "England", "", "", "", "john@example.com", "9", "101"])
            
            output_path = test_file.name.replace('.csv', '_out.csv')
        
        try:
            converter = SportPassportConverter(
                test_file.name,
                output_path,
                auto_confirm=False,
            )
            
            success = converter.run()
            # Should succeed - first column mapped, second skipped
            assert success is True
            
            # Verify multiple prompts were made
            assert mock_select.call_count >= 2
        
        finally:
            Path(test_file.name).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)
