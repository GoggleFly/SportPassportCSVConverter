"""Validation logic for Sport Passport data."""

from dataclasses import dataclass
from typing import Any, Optional
import re

from .schema import (
    FieldSpec, 
    FieldType, 
    SPORT_PASSPORT_SCHEMA,
    EXPECTED_COLUMN_COUNT,
    get_display_name,
)


@dataclass
class ValidationError:
    """Represents a validation error for a specific field."""
    row_index: int
    field_spec: FieldSpec
    value: Any
    error_message: str
    is_auto_fixable: bool = False
    suggested_fix: Optional[str] = None
    
    @property
    def field_name(self) -> str:
        return get_display_name(self.field_spec)


@dataclass
class RowValidationResult:
    """Result of validating a single row."""
    row_index: int
    row_data: dict[str, Any]
    errors: list[ValidationError]
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
    
    @property
    def has_auto_fixable_errors(self) -> bool:
        return any(e.is_auto_fixable for e in self.errors)
    
    @property
    def has_manual_fix_required(self) -> bool:
        return any(not e.is_auto_fixable for e in self.errors)
    
    def get_display_name(self) -> str:
        """Get a display name for this row (First Name + Surname)."""
        first = self.row_data.get("first_name", "") or ""
        last = self.row_data.get("surname", "") or ""
        if first or last:
            return f"{first} {last}".strip()
        return f"Row {self.row_index + 1}"


@dataclass
class ColumnMismatchError:
    """Represents a row with wrong number of columns (likely comma issue)."""
    row_index: int
    raw_values: list[str]
    expected_count: int
    actual_count: int
    
    @property
    def extra_columns(self) -> int:
        return self.actual_count - self.expected_count


class Validator:
    """Validates data against the Sport Passport schema."""
    
    def __init__(self):
        self.schema = SPORT_PASSPORT_SCHEMA
    
    def validate_field(
        self, 
        row_index: int, 
        field_spec: FieldSpec, 
        value: Any
    ) -> Optional[ValidationError]:
        """Validate a single field value against its specification."""
        
        # Convert to string for validation, handle None/NaN
        str_value = self._to_string(value)
        
        # Check required fields
        if field_spec.required and not str_value:
            return ValidationError(
                row_index=row_index,
                field_spec=field_spec,
                value=value,
                error_message=f"{get_display_name(field_spec)} is required",
                is_auto_fixable=False,
            )
        
        # Skip further validation if empty and not required
        if not str_value:
            return None
        
        # Type-specific validation
        if field_spec.field_type == FieldType.EMAIL:
            return self._validate_email(row_index, field_spec, str_value)
        
        elif field_spec.field_type == FieldType.DATE:
            return self._validate_date(row_index, field_spec, str_value, value)
        
        elif field_spec.field_type == FieldType.POSTCODE:
            return self._validate_postcode(row_index, field_spec, str_value)
        
        elif field_spec.field_type == FieldType.INTEGER:
            return self._validate_integer(row_index, field_spec, str_value)
        
        elif field_spec.field_type == FieldType.PHONE:
            return self._validate_phone(row_index, field_spec, str_value)
        
        elif field_spec.field_type == FieldType.TEXT:
            return self._validate_text(row_index, field_spec, str_value)
        
        return None
    
    def _to_string(self, value: Any) -> str:
        """Convert value to string, handling None and NaN."""
        if value is None:
            return ""
        if isinstance(value, float):
            import math
            if math.isnan(value):
                return ""
            # Check if it's a whole number
            if value.is_integer():
                return str(int(value))
        return str(value).strip()
    
    def _validate_email(
        self, 
        row_index: int, 
        field_spec: FieldSpec, 
        value: str
    ) -> Optional[ValidationError]:
        """Validate email format."""
        if not field_spec.matches_pattern(value):
            return ValidationError(
                row_index=row_index,
                field_spec=field_spec,
                value=value,
                error_message="Invalid email format",
                is_auto_fixable=False,
            )
        return None
    
    def _validate_date(
        self, 
        row_index: int, 
        field_spec: FieldSpec, 
        str_value: str,
        original_value: Any
    ) -> Optional[ValidationError]:
        """Validate date format - accepts various formats as auto-fixable."""
        from dateutil import parser
        from datetime import datetime
        
        # Check if already in correct format DD/MM/YYYY
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', str_value):
            parts = str_value.split('/')
            first, second, year = int(parts[0]), int(parts[1]), int(parts[2])
            
            # Try to interpret as UK format (DD/MM/YYYY) first
            uk_valid = False
            us_valid = False
            
            try:
                datetime(year, second, first)  # UK: day=first, month=second
                uk_valid = True
            except ValueError:
                pass
            
            try:
                datetime(year, first, second)  # US: month=first, day=second
                us_valid = True
            except ValueError:
                pass
            
            if uk_valid and not us_valid:
                # Only valid as UK format - it's correct
                return None
            
            if us_valid and not uk_valid:
                # Only valid as US format - auto-convert to UK
                suggested = f"{second:02d}/{first:02d}/{year}"
                return ValidationError(
                    row_index=row_index,
                    field_spec=field_spec,
                    value=str_value,
                    error_message="US date format detected (MM/DD/YYYY) - converting to UK format",
                    is_auto_fixable=True,
                    suggested_fix=suggested,
                )
            
            if uk_valid and us_valid:
                # Ambiguous - both interpretations are valid (e.g., 05/06/2001)
                # Assume UK format is correct since that's our target format
                return None
            
            # Neither interpretation is valid
            return ValidationError(
                row_index=row_index,
                field_spec=field_spec,
                value=str_value,
                error_message="Invalid date (day/month out of range)",
                is_auto_fixable=False,
            )
        
        # Try to parse as Excel serial date (integer)
        if isinstance(original_value, (int, float)) and not isinstance(original_value, bool):
            try:
                import math
                if not math.isnan(original_value):
                    # Excel serial date conversion
                    from datetime import datetime, timedelta
                    excel_epoch = datetime(1899, 12, 30)
                    parsed = excel_epoch + timedelta(days=int(original_value))
                    suggested = parsed.strftime('%d/%m/%Y')
                    return ValidationError(
                        row_index=row_index,
                        field_spec=field_spec,
                        value=str_value,
                        error_message="Date needs format conversion",
                        is_auto_fixable=True,
                        suggested_fix=suggested,
                    )
            except (ValueError, OverflowError):
                pass
        
        # Try to parse with dateutil
        try:
            # Handle datetime objects directly
            if hasattr(original_value, 'strftime'):
                suggested = original_value.strftime('%d/%m/%Y')
                return ValidationError(
                    row_index=row_index,
                    field_spec=field_spec,
                    value=str_value,
                    error_message="Date needs format conversion",
                    is_auto_fixable=True,
                    suggested_fix=suggested,
                )
            
            parsed = parser.parse(str_value, dayfirst=True)
            suggested = parsed.strftime('%d/%m/%Y')
            return ValidationError(
                row_index=row_index,
                field_spec=field_spec,
                value=str_value,
                error_message="Date needs format conversion",
                is_auto_fixable=True,
                suggested_fix=suggested,
            )
        except (ValueError, parser.ParserError):
            return ValidationError(
                row_index=row_index,
                field_spec=field_spec,
                value=str_value,
                error_message="Cannot parse date format",
                is_auto_fixable=False,
            )
    
    def _validate_postcode(
        self, 
        row_index: int, 
        field_spec: FieldSpec, 
        value: str
    ) -> Optional[ValidationError]:
        """Validate UK postcode format."""
        # Normalize for checking
        normalized = value.upper().replace(" ", "")
        
        # Add space in correct position for standard format check
        if len(normalized) >= 5:
            # UK postcodes have the last 3 characters as the inward code
            formatted = normalized[:-3] + " " + normalized[-3:]
            if field_spec.matches_pattern(formatted):
                if formatted != value:
                    return ValidationError(
                        row_index=row_index,
                        field_spec=field_spec,
                        value=value,
                        error_message="Postcode needs formatting",
                        is_auto_fixable=True,
                        suggested_fix=formatted,
                    )
                return None
        
        # Check if it matches pattern as-is
        if field_spec.matches_pattern(value):
            return None
        
        return ValidationError(
            row_index=row_index,
            field_spec=field_spec,
            value=value,
            error_message="Invalid UK postcode format",
            is_auto_fixable=False,
        )
    
    def _validate_integer(
        self, 
        row_index: int, 
        field_spec: FieldSpec, 
        value: str
    ) -> Optional[ValidationError]:
        """Validate integer fields."""
        try:
            int_val = int(float(value))
            
            if field_spec.min_value is not None and int_val < field_spec.min_value:
                return ValidationError(
                    row_index=row_index,
                    field_spec=field_spec,
                    value=value,
                    error_message=f"Value must be at least {field_spec.min_value}",
                    is_auto_fixable=False,
                )
            
            if field_spec.max_value is not None and int_val > field_spec.max_value:
                return ValidationError(
                    row_index=row_index,
                    field_spec=field_spec,
                    value=value,
                    error_message=f"Value must be at most {field_spec.max_value}",
                    is_auto_fixable=False,
                )
            
            return None
        except ValueError:
            return ValidationError(
                row_index=row_index,
                field_spec=field_spec,
                value=value,
                error_message="Must be a valid number",
                is_auto_fixable=False,
            )
    
    def _validate_phone(
        self, 
        row_index: int, 
        field_spec: FieldSpec, 
        value: str
    ) -> Optional[ValidationError]:
        """Validate phone number format."""
        # Remove common formatting characters for validation
        digits_only = re.sub(r'[\s\-\(\)\+]', '', value)
        
        if len(digits_only) < 10:
            return ValidationError(
                row_index=row_index,
                field_spec=field_spec,
                value=value,
                error_message="Phone number too short",
                is_auto_fixable=False,
            )
        
        if not digits_only.isdigit():
            return ValidationError(
                row_index=row_index,
                field_spec=field_spec,
                value=value,
                error_message="Phone number contains invalid characters",
                is_auto_fixable=False,
            )
        
        return None
    
    def _validate_text(
        self, 
        row_index: int, 
        field_spec: FieldSpec, 
        value: str
    ) -> Optional[ValidationError]:
        """Validate text fields with allowed values."""
        if field_spec.allowed_values:
            # Check for case-insensitive match
            normalized = value.strip()
            
            # Special handling for Gender field - M/F abbreviations
            if field_spec.name == "gender":
                gender_map = {
                    "m": "Male",
                    "f": "Female",
                    "o": "Other",
                    "male": "Male",
                    "female": "Female",
                    "other": "Other",
                }
                mapped = gender_map.get(normalized.lower())
                if mapped:
                    if normalized != mapped:
                        return ValidationError(
                            row_index=row_index,
                            field_spec=field_spec,
                            value=value,
                            error_message=f"Gender abbreviation expanded",
                            is_auto_fixable=True,
                            suggested_fix=mapped,
                        )
                    return None
            
            # Check for case-insensitive match against allowed values
            for allowed in field_spec.allowed_values:
                if normalized.lower() == allowed.lower():
                    if normalized != allowed:
                        return ValidationError(
                            row_index=row_index,
                            field_spec=field_spec,
                            value=value,
                            error_message=f"Value needs case correction",
                            is_auto_fixable=True,
                            suggested_fix=allowed,
                        )
                    return None
            
            # No match found
            allowed_str = ", ".join(field_spec.allowed_values)
            return ValidationError(
                row_index=row_index,
                field_spec=field_spec,
                value=value,
                error_message=f"Must be one of: {allowed_str}",
                is_auto_fixable=False,
            )
        
        return None
    
    def validate_row(
        self, 
        row_index: int, 
        row_data: dict[str, Any]
    ) -> RowValidationResult:
        """Validate all fields in a row."""
        errors = []
        
        for field_spec in self.schema:
            value = row_data.get(field_spec.name)
            error = self.validate_field(row_index, field_spec, value)
            if error:
                errors.append(error)
        
        return RowValidationResult(
            row_index=row_index,
            row_data=row_data,
            errors=errors,
        )
    
    def check_column_count(
        self, 
        row_index: int, 
        raw_values: list[str]
    ) -> Optional[ColumnMismatchError]:
        """Check if a row has the expected number of columns."""
        if len(raw_values) != EXPECTED_COLUMN_COUNT:
            return ColumnMismatchError(
                row_index=row_index,
                raw_values=raw_values,
                expected_count=EXPECTED_COLUMN_COUNT,
                actual_count=len(raw_values),
            )
        return None
