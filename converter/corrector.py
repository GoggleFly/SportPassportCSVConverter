"""Auto-correction functions for common data issues."""

from dataclasses import dataclass, field
from typing import Any, Optional
import re
from datetime import datetime, timedelta

from .schema import (
    FieldSpec,
    FieldType,
    SPORT_PASSPORT_SCHEMA,
    EXPECTED_COLUMN_COUNT,
    MEDICAL_CONDITIONS_INDEX,
    get_display_name,
)
from .validator import ValidationError, ColumnMismatchError


@dataclass
class CorrectionRecord:
    """Record of a correction applied to data."""
    row_index: int
    field_name: str
    original_value: Any
    corrected_value: Any
    correction_type: str  # e.g., "date_format", "whitespace", "case"


@dataclass
class CorrectionStats:
    """Statistics about corrections applied."""
    total_corrections: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    by_field: dict[str, int] = field(default_factory=dict)
    
    def record(self, correction: CorrectionRecord):
        self.total_corrections += 1
        self.by_type[correction.correction_type] = self.by_type.get(correction.correction_type, 0) + 1
        self.by_field[correction.field_name] = self.by_field.get(correction.field_name, 0) + 1


class Corrector:
    """Applies auto-corrections to data."""
    
    def __init__(self):
        self.stats = CorrectionStats()
        self.corrections: list[CorrectionRecord] = []
    
    def apply_auto_correction(
        self, 
        error: ValidationError
    ) -> Optional[str]:
        """Apply an auto-correction for a validation error if possible."""
        if error.is_auto_fixable and error.suggested_fix:
            correction = CorrectionRecord(
                row_index=error.row_index,
                field_name=get_display_name(error.field_spec),
                original_value=error.value,
                corrected_value=error.suggested_fix,
                correction_type=self._get_correction_type(error),
            )
            self.corrections.append(correction)
            self.stats.record(correction)
            return error.suggested_fix
        return None
    
    def _get_correction_type(self, error: ValidationError) -> str:
        """Determine the type of correction based on the error."""
        if error.field_spec.field_type == FieldType.DATE:
            if "US date" in error.error_message:
                return "us_to_uk_date"
            return "date_format"
        elif error.field_spec.field_type == FieldType.POSTCODE:
            return "postcode_format"
        elif error.field_spec.name == "gender":
            if "abbreviation" in error.error_message.lower():
                return "gender_abbreviation"
            return "gender_normalization"
        elif "case" in error.error_message.lower():
            return "case_normalization"
        return "format"
    
    def normalize_row(
        self, 
        row_index: int, 
        row_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply standard normalizations to all fields in a row."""
        normalized = {}
        
        for field_spec in SPORT_PASSPORT_SCHEMA:
            value = row_data.get(field_spec.name)
            original = value
            
            # Convert to string and handle None/NaN
            value = self._to_string(value)
            
            # Apply type-specific normalization
            if value:
                if field_spec.field_type == FieldType.TEXT:
                    value = self._normalize_text(value, field_spec)
                elif field_spec.field_type == FieldType.EMAIL:
                    value = self._normalize_email(value)
                elif field_spec.field_type == FieldType.POSTCODE:
                    value = self._normalize_postcode(value)
                elif field_spec.field_type == FieldType.PHONE:
                    value = self._normalize_phone(value)
                elif field_spec.field_type == FieldType.DATE:
                    value = self._normalize_date(value, original)
                elif field_spec.field_type == FieldType.INTEGER:
                    value = self._normalize_integer(value)
            
            # Record if changed
            original_str = self._to_string(original)
            if value != original_str and original_str:
                correction = CorrectionRecord(
                    row_index=row_index,
                    field_name=get_display_name(field_spec),
                    original_value=original_str,
                    corrected_value=value,
                    correction_type="normalization",
                )
                self.corrections.append(correction)
                self.stats.record(correction)
            
            normalized[field_spec.name] = value
        
        return normalized
    
    def _to_string(self, value: Any) -> str:
        """Convert value to string, handling None and NaN."""
        if value is None:
            return ""
        if isinstance(value, float):
            import math
            if math.isnan(value):
                return ""
            if value.is_integer():
                return str(int(value))
        return str(value).strip()
    
    def _normalize_text(self, value: str, field_spec: FieldSpec) -> str:
        """Normalize text fields."""
        value = value.strip()
        
        # For name fields, apply title case
        if field_spec.name in ("first_name", "surname"):
            # Only apply if all lowercase or all uppercase
            if value.islower() or value.isupper():
                value = value.title()
        
        # For fields with allowed values, match case
        if field_spec.allowed_values:
            for allowed in field_spec.allowed_values:
                if value.lower() == allowed.lower():
                    return allowed
        
        return value
    
    def _normalize_email(self, value: str) -> str:
        """Normalize email addresses."""
        return value.strip().lower()
    
    def _normalize_postcode(self, value: str) -> str:
        """Normalize UK postcodes."""
        # Remove extra spaces, convert to uppercase
        value = re.sub(r'\s+', '', value.strip().upper())
        
        # Add space before last 3 characters (inward code)
        if len(value) >= 5:
            value = value[:-3] + " " + value[-3:]
        
        return value
    
    def _normalize_phone(self, value: str) -> str:
        """Normalize phone numbers - keep as-is but trim."""
        return value.strip()
    
    def _normalize_date(self, value: str, original: Any) -> str:
        """Attempt to normalize date to DD/MM/YYYY format."""
        from dateutil import parser
        
        # Already in correct format?
        if re.match(r'^\d{2}/\d{2}/\d{4}$', value):
            return value
        
        # Handle datetime objects
        if hasattr(original, 'strftime'):
            return original.strftime('%d/%m/%Y')
        
        # Handle Excel serial dates
        if isinstance(original, (int, float)) and not isinstance(original, bool):
            try:
                import math
                if not math.isnan(original):
                    excel_epoch = datetime(1899, 12, 30)
                    parsed = excel_epoch + timedelta(days=int(original))
                    return parsed.strftime('%d/%m/%Y')
            except (ValueError, OverflowError):
                pass
        
        # Try dateutil parser
        try:
            parsed = parser.parse(value, dayfirst=True)
            return parsed.strftime('%d/%m/%Y')
        except (ValueError, parser.ParserError):
            pass
        
        return value
    
    def _normalize_integer(self, value: str) -> str:
        """Normalize integer values."""
        try:
            return str(int(float(value)))
        except ValueError:
            return value
    
    def attempt_csv_repair(
        self, 
        error: ColumnMismatchError
    ) -> Optional[list[str]]:
        """
        Attempt to repair a CSV row with too many columns.
        
        Returns repaired values list if successful, None if manual intervention needed.
        """
        if error.actual_count <= error.expected_count:
            # Too few columns - can't auto-repair
            return None
        
        extra = error.extra_columns
        values = error.raw_values
        
        # The medical conditions field is most likely culprit
        # Try merging columns starting at medical conditions index
        med_idx = MEDICAL_CONDITIONS_INDEX
        
        # Merge the extra columns into medical conditions
        end_idx = med_idx + extra + 1
        
        if end_idx > len(values):
            return None
        
        # Build repaired row
        repaired = values[:med_idx]
        
        # Merge medical conditions columns back together
        merged_medical = ", ".join(values[med_idx:end_idx])
        repaired.append(merged_medical)
        
        # Add remaining columns
        repaired.extend(values[end_idx:])
        
        if len(repaired) != error.expected_count:
            return None
        
        # Validate the repair makes sense
        # Check if field after medical conditions looks like an address or date
        if len(repaired) > med_idx + 1:
            next_field = repaired[med_idx + 1]  # Should be Address1
            # If it looks like a date or valid address, repair is likely correct
            if self._looks_like_address_or_empty(next_field):
                return repaired
        
        # Can't confidently repair
        return None
    
    def _looks_like_address_or_empty(self, value: str) -> bool:
        """Check if a value looks like an address (or is empty)."""
        if not value or not value.strip():
            return True
        
        # Common address patterns
        address_patterns = [
            r'^\d+\s+\w+',  # Starts with number and word (e.g., "12 High Street")
            r'^\w+\s+\w+\s+(road|street|lane|avenue|drive|close|way|court)',  # Has street type
            r'^flat\s+\d+',  # Flat number
            r'^unit\s+\d+',  # Unit number
        ]
        
        value_lower = value.lower().strip()
        for pattern in address_patterns:
            if re.match(pattern, value_lower, re.IGNORECASE):
                return True
        
        return False
    
    def get_summary(self) -> dict:
        """Get a summary of all corrections applied."""
        return {
            "total": self.stats.total_corrections,
            "by_type": dict(self.stats.by_type),
            "by_field": dict(self.stats.by_field),
        }
