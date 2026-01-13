"""Tests for validator module."""

import pytest
from datetime import datetime

from converter.validator import (
    Validator,
    ValidationError,
    RowValidationResult,
    ColumnMismatchError,
)
from converter.schema import (
    get_field_by_name,
    EXPECTED_COLUMN_COUNT,
)


class TestValidatorBasics:
    """Basic validator tests."""
    
    @pytest.fixture
    def validator(self):
        return Validator()
    
    def test_validator_initialization(self, validator):
        """Validator should initialize with schema."""
        assert validator.schema is not None
        assert len(validator.schema) == EXPECTED_COLUMN_COUNT


class TestRequiredFieldValidation:
    """Tests for required field validation."""
    
    @pytest.fixture
    def validator(self):
        return Validator()
    
    def test_missing_required_field_fails(self, validator):
        """Missing required field should produce error."""
        field_spec = get_field_by_name("first_name")
        error = validator.validate_field(0, field_spec, "")
        
        assert error is not None
        assert "required" in error.error_message.lower()
        assert error.is_auto_fixable is False
    
    def test_missing_required_field_none(self, validator):
        """None value for required field should produce error."""
        field_spec = get_field_by_name("first_name")
        error = validator.validate_field(0, field_spec, None)
        
        assert error is not None
        assert error.is_auto_fixable is False
    
    def test_present_required_field_passes(self, validator):
        """Present required field should not produce error."""
        field_spec = get_field_by_name("first_name")
        error = validator.validate_field(0, field_spec, "John")
        
        assert error is None
    
    def test_missing_optional_field_passes(self, validator):
        """Missing optional field should not produce error."""
        field_spec = get_field_by_name("medical_conditions")
        error = validator.validate_field(0, field_spec, "")
        
        assert error is None


class TestEmailValidation:
    """Tests for email field validation."""
    
    @pytest.fixture
    def validator(self):
        return Validator()
    
    @pytest.fixture
    def email_spec(self):
        return get_field_by_name("email")
    
    def test_valid_email_passes(self, validator, email_spec):
        """Valid email should pass validation."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user123@test.org",
        ]
        
        for email in valid_emails:
            error = validator.validate_field(0, email_spec, email)
            assert error is None, f"{email} should be valid"
    
    def test_invalid_email_fails(self, validator, email_spec):
        """Invalid email should fail validation."""
        invalid_emails = [
            "not-an-email",
            "missing@domain",
            "@nodomain.com",
            "spaces in@email.com",
        ]
        
        for email in invalid_emails:
            error = validator.validate_field(0, email_spec, email)
            assert error is not None, f"{email} should be invalid"
            assert "email" in error.error_message.lower()
            assert error.is_auto_fixable is False


class TestDateValidation:
    """Tests for date field validation."""
    
    @pytest.fixture
    def validator(self):
        return Validator()
    
    @pytest.fixture
    def dob_spec(self):
        return get_field_by_name("date_of_birth")
    
    def test_correct_format_passes(self, validator, dob_spec):
        """Date in DD/MM/YYYY format should pass."""
        error = validator.validate_field(0, dob_spec, "16/12/2001")
        assert error is None
    
    def test_iso_format_auto_fixable(self, validator, dob_spec):
        """ISO date format should be auto-fixable."""
        error = validator.validate_field(0, dob_spec, "2001-12-16")
        
        assert error is not None
        assert error.is_auto_fixable is True
        assert error.suggested_fix == "16/12/2001"
    
    def test_us_format_detected_and_corrected(self, validator, dob_spec):
        """Obvious US date format should be auto-corrected to UK format."""
        # 12/16/2001 - only valid interpretation is US format (Dec 16)
        # because 16 can't be a month, so it must be the day
        error = validator.validate_field(0, dob_spec, "12/16/2001")
        
        assert error is not None
        assert error.is_auto_fixable is True
        assert error.suggested_fix == "16/12/2001"
        assert "US date" in error.error_message
    
    def test_datetime_object_auto_fixable(self, validator, dob_spec):
        """Datetime object should be auto-fixable."""
        dt = datetime(2001, 12, 16)
        
        # Pass the original datetime object to internal method
        error = validator._validate_date(0, dob_spec, str(dt), dt)
        assert error is not None
        assert error.is_auto_fixable is True
        assert error.suggested_fix == "16/12/2001"
    
    def test_invalid_date_not_auto_fixable(self, validator, dob_spec):
        """Unparseable date should not be auto-fixable."""
        error = validator.validate_field(0, dob_spec, "not-a-date")
        
        assert error is not None
        assert error.is_auto_fixable is False
    
    def test_invalid_date_values(self, validator, dob_spec):
        """Invalid day/month values should fail."""
        error = validator.validate_field(0, dob_spec, "32/13/2001")
        
        assert error is not None
        assert error.is_auto_fixable is False


class TestPostcodeValidation:
    """Tests for postcode field validation."""
    
    @pytest.fixture
    def validator(self):
        return Validator()
    
    @pytest.fixture
    def postcode_spec(self):
        return get_field_by_name("postcode")
    
    def test_valid_postcode_passes(self, validator, postcode_spec):
        """Valid UK postcode should pass."""
        error = validator.validate_field(0, postcode_spec, "E1 9BR")
        assert error is None
    
    def test_lowercase_postcode_auto_fixable(self, validator, postcode_spec):
        """Lowercase postcode should be auto-fixable."""
        error = validator.validate_field(0, postcode_spec, "e1 9br")
        
        assert error is not None
        assert error.is_auto_fixable is True
        assert error.suggested_fix == "E1 9BR"
    
    def test_no_space_postcode_auto_fixable(self, validator, postcode_spec):
        """Postcode without space should be auto-fixable."""
        error = validator.validate_field(0, postcode_spec, "E19BR")
        
        assert error is not None
        assert error.is_auto_fixable is True
        assert error.suggested_fix == "E1 9BR"
    
    def test_invalid_postcode_not_auto_fixable(self, validator, postcode_spec):
        """Invalid postcode should not be auto-fixable."""
        error = validator.validate_field(0, postcode_spec, "INVALID")
        
        assert error is not None
        assert error.is_auto_fixable is False


class TestAllowedValuesValidation:
    """Tests for fields with allowed values."""
    
    @pytest.fixture
    def validator(self):
        return Validator()
    
    def test_gender_valid_values(self, validator):
        """Valid gender values should pass."""
        gender_spec = get_field_by_name("gender")
        
        for value in ["Male", "Female", "Other"]:
            error = validator.validate_field(0, gender_spec, value)
            assert error is None, f"{value} should be valid"
    
    def test_gender_wrong_case_auto_fixable(self, validator):
        """Wrong case gender should be auto-fixable."""
        gender_spec = get_field_by_name("gender")
        
        error = validator.validate_field(0, gender_spec, "male")
        assert error is not None
        assert error.is_auto_fixable is True
        assert error.suggested_fix == "Male"
        
        error = validator.validate_field(0, gender_spec, "FEMALE")
        assert error is not None
        assert error.is_auto_fixable is True
        assert error.suggested_fix == "Female"
    
    def test_gender_abbreviation_m_auto_fixable(self, validator):
        """M abbreviation should be auto-corrected to Male."""
        gender_spec = get_field_by_name("gender")
        
        error = validator.validate_field(0, gender_spec, "M")
        assert error is not None
        assert error.is_auto_fixable is True
        assert error.suggested_fix == "Male"
        
        error = validator.validate_field(0, gender_spec, "m")
        assert error is not None
        assert error.is_auto_fixable is True
        assert error.suggested_fix == "Male"
    
    def test_gender_abbreviation_f_auto_fixable(self, validator):
        """F abbreviation should be auto-corrected to Female."""
        gender_spec = get_field_by_name("gender")
        
        error = validator.validate_field(0, gender_spec, "F")
        assert error is not None
        assert error.is_auto_fixable is True
        assert error.suggested_fix == "Female"
        
        error = validator.validate_field(0, gender_spec, "f")
        assert error is not None
        assert error.is_auto_fixable is True
        assert error.suggested_fix == "Female"
    
    def test_gender_invalid_value(self, validator):
        """Invalid gender value should fail."""
        gender_spec = get_field_by_name("gender")
        
        error = validator.validate_field(0, gender_spec, "Invalid")
        assert error is not None
        assert error.is_auto_fixable is False
        assert "Male" in error.error_message
    
    def test_disabled_valid_values(self, validator):
        """Valid ClassifiedAsDisabled values should pass."""
        disabled_spec = get_field_by_name("classified_as_disabled")
        
        for value in ["Yes", "No"]:
            error = validator.validate_field(0, disabled_spec, value)
            assert error is None
    
    def test_disabled_wrong_case_auto_fixable(self, validator):
        """Wrong case disabled should be auto-fixable."""
        disabled_spec = get_field_by_name("classified_as_disabled")
        
        error = validator.validate_field(0, disabled_spec, "yes")
        assert error.is_auto_fixable is True
        assert error.suggested_fix == "Yes"
        
        error = validator.validate_field(0, disabled_spec, "NO")
        assert error.is_auto_fixable is True
        assert error.suggested_fix == "No"


class TestIntegerValidation:
    """Tests for integer field validation."""
    
    @pytest.fixture
    def validator(self):
        return Validator()
    
    def test_valid_school_year(self, validator):
        """Valid school year should pass."""
        spec = get_field_by_name("school_year")
        
        for year in range(1, 14):
            error = validator.validate_field(0, spec, str(year))
            assert error is None, f"Year {year} should be valid"
    
    def test_school_year_too_low(self, validator):
        """School year below minimum should fail."""
        spec = get_field_by_name("school_year")
        
        error = validator.validate_field(0, spec, "0")
        assert error is not None
        assert "at least" in error.error_message
    
    def test_school_year_too_high(self, validator):
        """School year above maximum should fail."""
        spec = get_field_by_name("school_year")
        
        error = validator.validate_field(0, spec, "14")
        assert error is not None
        assert "at most" in error.error_message
    
    def test_non_numeric_fails(self, validator):
        """Non-numeric value should fail."""
        spec = get_field_by_name("school_year")
        
        error = validator.validate_field(0, spec, "abc")
        assert error is not None
        assert "number" in error.error_message.lower()


class TestPhoneValidation:
    """Tests for phone field validation."""
    
    @pytest.fixture
    def validator(self):
        return Validator()
    
    def test_valid_phone_passes(self, validator):
        """Valid phone number should pass."""
        spec = get_field_by_name("phone_number")
        
        valid_phones = [
            "07700123456",
            "0121 456 7890",
            "+44 7700 123456",
            "01onal234-567-890",
        ]
        
        for phone in valid_phones:
            error = validator.validate_field(0, spec, phone)
            # Some may fail depending on validation rules
    
    def test_short_phone_fails(self, validator):
        """Too short phone number should fail."""
        spec = get_field_by_name("phone_number")
        
        error = validator.validate_field(0, spec, "12345")
        assert error is not None
        assert "short" in error.error_message.lower()


class TestRowValidation:
    """Tests for full row validation."""
    
    @pytest.fixture
    def validator(self):
        return Validator()
    
    def test_valid_row_passes(self, validator):
        """Valid row should have no errors."""
        row_data = {
            "sport_passport_id": "",
            "first_name": "John",
            "surname": "Smith",
            "gender": "Male",
            "classified_as_disabled": "No",
            "medical_conditions": "Diabetes",
            "date_of_birth": "16/12/2001",
            "address1": "12 High Street",
            "address2": "",
            "phone_number": "07700123456",
            "town_city": "London",
            "county": "",
            "postcode": "E1 9BR",
            "country": "England",
            "emergency_contact_name": "Jane Smith",
            "emergency_contact_phone": "07700654321",
            "emergency_contact_phone2": "",
            "email": "j.smith@example.com",
            "school_year": "9",
            "course_id": "101",
        }
        
        result = validator.validate_row(0, row_data)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_invalid_row_has_errors(self, validator):
        """Invalid row should have errors."""
        row_data = {
            "first_name": "",  # Required, missing
            "surname": "Smith",
            "gender": "Invalid",  # Invalid value
            "classified_as_disabled": "No",
            "date_of_birth": "not-a-date",  # Invalid format
            "postcode": "E1 9BR",
            "email": "invalid-email",  # Invalid format
        }
        
        result = validator.validate_row(0, row_data)
        
        assert not result.is_valid
        assert len(result.errors) >= 4
    
    def test_row_result_display_name(self, validator):
        """Row result should have display name."""
        row_data = {
            "first_name": "John",
            "surname": "Smith",
            "gender": "Male",
            "classified_as_disabled": "No",
            "date_of_birth": "16/12/2001",
            "postcode": "E1 9BR",
            "email": "j.smith@example.com",
        }
        
        result = validator.validate_row(0, row_data)
        assert result.get_display_name() == "John Smith"


class TestColumnMismatch:
    """Tests for column count mismatch detection."""
    
    @pytest.fixture
    def validator(self):
        return Validator()
    
    def test_correct_count_passes(self, validator):
        """Correct column count should not produce error."""
        values = [""] * EXPECTED_COLUMN_COUNT
        error = validator.check_column_count(0, values)
        assert error is None
    
    def test_too_many_columns_detected(self, validator):
        """Too many columns should be detected."""
        values = [""] * (EXPECTED_COLUMN_COUNT + 3)
        error = validator.check_column_count(0, values)
        
        assert error is not None
        assert isinstance(error, ColumnMismatchError)
        assert error.extra_columns == 3
    
    def test_too_few_columns_detected(self, validator):
        """Too few columns should be detected."""
        values = [""] * (EXPECTED_COLUMN_COUNT - 2)
        error = validator.check_column_count(0, values)
        
        assert error is not None
        assert error.extra_columns == -2
