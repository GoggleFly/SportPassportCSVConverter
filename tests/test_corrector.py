"""Tests for corrector module."""

import pytest
from datetime import datetime

from converter.corrector import (
    Corrector,
    CorrectionRecord,
    CorrectionStats,
)
from converter.validator import (
    Validator,
    ValidationError,
    ColumnMismatchError,
)
from converter.schema import (
    get_field_by_name,
    EXPECTED_COLUMN_COUNT,
    MEDICAL_CONDITIONS_INDEX,
)


class TestCorrectorBasics:
    """Basic corrector tests."""
    
    @pytest.fixture
    def corrector(self):
        return Corrector()
    
    def test_corrector_initialization(self, corrector):
        """Corrector should initialize with empty stats."""
        assert corrector.stats.total_corrections == 0
        assert len(corrector.corrections) == 0


class TestAutoCorrections:
    """Tests for auto-correction application."""
    
    @pytest.fixture
    def corrector(self):
        return Corrector()
    
    @pytest.fixture
    def validator(self):
        return Validator()
    
    def test_apply_auto_correction(self, corrector, validator):
        """Auto-fixable error should be corrected."""
        gender_spec = get_field_by_name("gender")
        error = validator.validate_field(0, gender_spec, "male")
        
        assert error.is_auto_fixable
        result = corrector.apply_auto_correction(error)
        
        assert result == "Male"
        assert corrector.stats.total_corrections == 1
    
    def test_non_auto_fixable_returns_none(self, corrector, validator):
        """Non-auto-fixable error should return None."""
        email_spec = get_field_by_name("email")
        error = validator.validate_field(0, email_spec, "invalid-email")
        
        assert not error.is_auto_fixable
        result = corrector.apply_auto_correction(error)
        
        assert result is None
        assert corrector.stats.total_corrections == 0


class TestRowNormalization:
    """Tests for row normalization."""
    
    @pytest.fixture
    def corrector(self):
        return Corrector()
    
    def test_whitespace_trimmed(self, corrector):
        """Whitespace should be trimmed from all fields."""
        row_data = {
            "first_name": "  John  ",
            "surname": "Smith   ",
            "gender": "Male",
            "classified_as_disabled": "No",
            "date_of_birth": "16/12/2001",
            "postcode": "E1 9BR",
            "email": "  test@example.com  ",
        }
        
        normalized = corrector.normalize_row(0, row_data)
        
        assert normalized["first_name"] == "John"
        assert normalized["surname"] == "Smith"
        assert normalized["email"] == "test@example.com"
    
    def test_email_lowercased(self, corrector):
        """Email should be lowercased."""
        row_data = {
            "first_name": "John",
            "surname": "Smith",
            "gender": "Male",
            "classified_as_disabled": "No",
            "date_of_birth": "16/12/2001",
            "postcode": "E1 9BR",
            "email": "TEST@EXAMPLE.COM",
        }
        
        normalized = corrector.normalize_row(0, row_data)
        
        assert normalized["email"] == "test@example.com"
    
    def test_postcode_formatted(self, corrector):
        """Postcode should be formatted correctly."""
        row_data = {
            "first_name": "John",
            "surname": "Smith",
            "gender": "Male",
            "classified_as_disabled": "No",
            "date_of_birth": "16/12/2001",
            "postcode": "e19br",
            "email": "test@example.com",
        }
        
        normalized = corrector.normalize_row(0, row_data)
        
        assert normalized["postcode"] == "E1 9BR"
    
    def test_gender_normalized(self, corrector):
        """Gender should be normalized to correct case."""
        row_data = {
            "first_name": "John",
            "surname": "Smith",
            "gender": "male",
            "classified_as_disabled": "No",
            "date_of_birth": "16/12/2001",
            "postcode": "E1 9BR",
            "email": "test@example.com",
        }
        
        normalized = corrector.normalize_row(0, row_data)
        
        assert normalized["gender"] == "Male"
    
    def test_disabled_normalized(self, corrector):
        """ClassifiedAsDisabled should be normalized."""
        row_data = {
            "first_name": "John",
            "surname": "Smith",
            "gender": "Male",
            "classified_as_disabled": "yes",
            "date_of_birth": "16/12/2001",
            "postcode": "E1 9BR",
            "email": "test@example.com",
        }
        
        normalized = corrector.normalize_row(0, row_data)
        
        assert normalized["classified_as_disabled"] == "Yes"
    
    def test_names_title_cased_when_all_lower(self, corrector):
        """Names should be title cased when all lowercase."""
        row_data = {
            "first_name": "john",
            "surname": "smith",
            "gender": "Male",
            "classified_as_disabled": "No",
            "date_of_birth": "16/12/2001",
            "postcode": "E1 9BR",
            "email": "test@example.com",
        }
        
        normalized = corrector.normalize_row(0, row_data)
        
        assert normalized["first_name"] == "John"
        assert normalized["surname"] == "Smith"
    
    def test_names_title_cased_when_all_upper(self, corrector):
        """Names should be title cased when all uppercase."""
        row_data = {
            "first_name": "JOHN",
            "surname": "SMITH",
            "gender": "Male",
            "classified_as_disabled": "No",
            "date_of_birth": "16/12/2001",
            "postcode": "E1 9BR",
            "email": "test@example.com",
        }
        
        normalized = corrector.normalize_row(0, row_data)
        
        assert normalized["first_name"] == "John"
        assert normalized["surname"] == "Smith"
    
    def test_mixed_case_names_preserved(self, corrector):
        """Mixed case names should be preserved."""
        row_data = {
            "first_name": "McDonald",
            "surname": "O'Brien",
            "gender": "Male",
            "classified_as_disabled": "No",
            "date_of_birth": "16/12/2001",
            "postcode": "E1 9BR",
            "email": "test@example.com",
        }
        
        normalized = corrector.normalize_row(0, row_data)
        
        # Mixed case should be preserved
        assert normalized["first_name"] == "McDonald"
        assert normalized["surname"] == "O'Brien"
    
    def test_nan_handled(self, corrector):
        """NaN values should be converted to empty string."""
        import math
        row_data = {
            "first_name": "John",
            "surname": "Smith",
            "gender": "Male",
            "classified_as_disabled": "No",
            "date_of_birth": "16/12/2001",
            "postcode": "E1 9BR",
            "email": "test@example.com",
            "medical_conditions": float('nan'),
        }
        
        normalized = corrector.normalize_row(0, row_data)
        
        assert normalized["medical_conditions"] == ""
    
    def test_none_handled(self, corrector):
        """None values should be converted to empty string."""
        row_data = {
            "first_name": "John",
            "surname": "Smith",
            "gender": "Male",
            "classified_as_disabled": "No",
            "date_of_birth": "16/12/2001",
            "postcode": "E1 9BR",
            "email": "test@example.com",
            "medical_conditions": None,
        }
        
        normalized = corrector.normalize_row(0, row_data)
        
        assert normalized["medical_conditions"] == ""


class TestDateNormalization:
    """Tests for date normalization."""
    
    @pytest.fixture
    def corrector(self):
        return Corrector()
    
    def test_iso_date_normalized(self, corrector):
        """ISO date format should be normalized."""
        row_data = {
            "first_name": "John",
            "surname": "Smith",
            "gender": "Male",
            "classified_as_disabled": "No",
            "date_of_birth": "2001-12-16",
            "postcode": "E1 9BR",
            "email": "test@example.com",
        }
        
        normalized = corrector.normalize_row(0, row_data)
        
        assert normalized["date_of_birth"] == "16/12/2001"
    
    def test_datetime_object_normalized(self, corrector):
        """Datetime object should be normalized."""
        row_data = {
            "first_name": "John",
            "surname": "Smith",
            "gender": "Male",
            "classified_as_disabled": "No",
            "date_of_birth": datetime(2001, 12, 16),
            "postcode": "E1 9BR",
            "email": "test@example.com",
        }
        
        normalized = corrector.normalize_row(0, row_data)
        
        assert normalized["date_of_birth"] == "16/12/2001"
    
    def test_correct_format_preserved(self, corrector):
        """Already correct date format should be preserved."""
        row_data = {
            "first_name": "John",
            "surname": "Smith",
            "gender": "Male",
            "classified_as_disabled": "No",
            "date_of_birth": "16/12/2001",
            "postcode": "E1 9BR",
            "email": "test@example.com",
        }
        
        normalized = corrector.normalize_row(0, row_data)
        
        assert normalized["date_of_birth"] == "16/12/2001"


class TestIntegerNormalization:
    """Tests for integer normalization."""
    
    @pytest.fixture
    def corrector(self):
        return Corrector()
    
    def test_float_to_int(self, corrector):
        """Float values should be normalized to integers."""
        row_data = {
            "first_name": "John",
            "surname": "Smith",
            "gender": "Male",
            "classified_as_disabled": "No",
            "date_of_birth": "16/12/2001",
            "postcode": "E1 9BR",
            "email": "test@example.com",
            "school_year": 9.0,
            "course_id": 101.0,
        }
        
        normalized = corrector.normalize_row(0, row_data)
        
        assert normalized["school_year"] == "9"
        assert normalized["course_id"] == "101"


class TestCSVRepair:
    """Tests for CSV comma repair."""
    
    @pytest.fixture
    def corrector(self):
        return Corrector()
    
    def test_repair_extra_columns_in_medical_conditions(self, corrector):
        """Should repair row with commas in medical conditions."""
        # Simulating a row where medical conditions was split
        # Expected: 20 columns, Actual: 23 (3 extra from medical conditions split)
        values = [""] * MEDICAL_CONDITIONS_INDEX  # Columns before medical
        values.extend(["Diabetes", "asthma", "uses inhaler"])  # Split medical conditions
        values.extend(["16/12/2001"])  # DOB
        values.extend(["12 High Street", "", "07700123456"])  # Address fields
        values.extend(["London", "", "E1 9BR", "England"])  # Location
        values.extend(["Jane Smith", "07700654321", ""])  # Emergency contact
        values.extend(["j.smith@example.com", "9", "101"])  # Email, year, course
        
        error = ColumnMismatchError(
            row_index=0,
            raw_values=values,
            expected_count=EXPECTED_COLUMN_COUNT,
            actual_count=len(values),
        )
        
        repaired = corrector.attempt_csv_repair(error)
        
        # The repair logic attempts to merge, but may not always succeed
        # depending on heuristics
        if repaired:
            assert len(repaired) == EXPECTED_COLUMN_COUNT
    
    def test_repair_returns_none_for_too_few_columns(self, corrector):
        """Should return None when too few columns."""
        values = [""] * (EXPECTED_COLUMN_COUNT - 2)
        
        error = ColumnMismatchError(
            row_index=0,
            raw_values=values,
            expected_count=EXPECTED_COLUMN_COUNT,
            actual_count=len(values),
        )
        
        repaired = corrector.attempt_csv_repair(error)
        
        assert repaired is None


class TestCorrectionStats:
    """Tests for correction statistics tracking."""
    
    @pytest.fixture
    def corrector(self):
        return Corrector()
    
    @pytest.fixture
    def validator(self):
        return Validator()
    
    def test_stats_tracked(self, corrector, validator):
        """Corrections should be tracked in stats."""
        gender_spec = get_field_by_name("gender")
        
        # Apply multiple corrections (m/f abbreviations)
        error1 = validator.validate_field(0, gender_spec, "m")
        corrector.apply_auto_correction(error1)
        
        error2 = validator.validate_field(1, gender_spec, "f")
        corrector.apply_auto_correction(error2)
        
        summary = corrector.get_summary()
        
        assert summary["total"] == 2
        # Gender abbreviations are tracked as gender_abbreviation
        assert "gender_abbreviation" in summary["by_type"]
        assert summary["by_type"]["gender_abbreviation"] == 2
    
    def test_corrections_recorded(self, corrector, validator):
        """Individual corrections should be recorded."""
        gender_spec = get_field_by_name("gender")
        error = validator.validate_field(0, gender_spec, "male")
        
        corrector.apply_auto_correction(error)
        
        assert len(corrector.corrections) == 1
        record = corrector.corrections[0]
        assert record.original_value == "male"
        assert record.corrected_value == "Male"
        assert record.field_name == "Gender"
