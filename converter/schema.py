"""Sport Passport schema definition with field specifications and validation rules."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
import re


class FieldType(Enum):
    """Data types for schema fields."""
    TEXT = "text"
    DATE = "date"
    INTEGER = "integer"
    EMAIL = "email"
    POSTCODE = "postcode"
    PHONE = "phone"


@dataclass
class FieldSpec:
    """Specification for a single field in the schema."""
    name: str
    column_header: str
    field_type: FieldType
    required: bool = False
    allowed_values: Optional[list[str]] = None
    pattern: Optional[str] = None
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    
    def __post_init__(self):
        if self.pattern:
            self._compiled_pattern = re.compile(self.pattern, re.IGNORECASE)
        else:
            self._compiled_pattern = None
    
    def matches_pattern(self, value: str) -> bool:
        """Check if value matches the field's regex pattern."""
        if not self._compiled_pattern:
            return True
        return bool(self._compiled_pattern.match(value))


# UK Postcode regex pattern
UK_POSTCODE_PATTERN = r'^[A-Z]{1,2}[0-9][0-9A-Z]?\s*[0-9][A-Z]{2}$'

# Email regex pattern (simplified but effective)
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# UK Phone pattern (flexible)
UK_PHONE_PATTERN = r'^[\d\s\-\+\(\)]{10,}$'


# Define the Sport Passport schema - fields in exact column order
SPORT_PASSPORT_SCHEMA: list[FieldSpec] = [
    FieldSpec(
        name="sport_passport_id",
        column_header="Sport Passport ID",
        field_type=FieldType.TEXT,
        required=False,
    ),
    FieldSpec(
        name="first_name",
        column_header="First Name*",
        field_type=FieldType.TEXT,
        required=True,
    ),
    FieldSpec(
        name="surname",
        column_header="Surname*",
        field_type=FieldType.TEXT,
        required=True,
    ),
    FieldSpec(
        name="gender",
        column_header="Gender*",
        field_type=FieldType.TEXT,
        required=True,
        allowed_values=["Male", "Female", "Other"],
    ),
    FieldSpec(
        name="classified_as_disabled",
        column_header="ClassifiedAsDisabled*",
        field_type=FieldType.TEXT,
        required=True,
        allowed_values=["Yes", "No"],
    ),
    FieldSpec(
        name="medical_conditions",
        column_header="MedicalConditions",
        field_type=FieldType.TEXT,
        required=False,
    ),
    FieldSpec(
        name="date_of_birth",
        column_header="DateOfBirth*",
        field_type=FieldType.DATE,
        required=True,
    ),
    FieldSpec(
        name="address1",
        column_header="Address1",
        field_type=FieldType.TEXT,
        required=False,
    ),
    FieldSpec(
        name="address2",
        column_header="Address2",
        field_type=FieldType.TEXT,
        required=False,
    ),
    FieldSpec(
        name="phone_number",
        column_header="PhoneNumber",
        field_type=FieldType.PHONE,
        required=False,
        pattern=UK_PHONE_PATTERN,
    ),
    FieldSpec(
        name="town_city",
        column_header="TownCity",
        field_type=FieldType.TEXT,
        required=False,
    ),
    FieldSpec(
        name="county",
        column_header="County",
        field_type=FieldType.TEXT,
        required=False,
    ),
    FieldSpec(
        name="postcode",
        column_header="Postcode*",
        field_type=FieldType.POSTCODE,
        required=True,
        pattern=UK_POSTCODE_PATTERN,
    ),
    FieldSpec(
        name="country",
        column_header="Country",
        field_type=FieldType.TEXT,
        required=False,
    ),
    FieldSpec(
        name="emergency_contact_name",
        column_header="EmergencyContactName",
        field_type=FieldType.TEXT,
        required=False,
    ),
    FieldSpec(
        name="emergency_contact_phone",
        column_header="EmergencyContactPhone",
        field_type=FieldType.PHONE,
        required=False,
        pattern=UK_PHONE_PATTERN,
    ),
    FieldSpec(
        name="emergency_contact_phone2",
        column_header="EmergencyContactPhone2",
        field_type=FieldType.PHONE,
        required=False,
        pattern=UK_PHONE_PATTERN,
    ),
    FieldSpec(
        name="email",
        column_header="Email*",
        field_type=FieldType.EMAIL,
        required=True,
        pattern=EMAIL_PATTERN,
    ),
    FieldSpec(
        name="school_year",
        column_header="SchoolYear",
        field_type=FieldType.INTEGER,
        required=False,
        min_value=1,
        max_value=13,
    ),
    FieldSpec(
        name="course_id",
        column_header="CourseID",
        field_type=FieldType.INTEGER,
        required=False,
    ),
]

# Number of expected columns
EXPECTED_COLUMN_COUNT = len(SPORT_PASSPORT_SCHEMA)

# Column headers in order
COLUMN_HEADERS = [spec.column_header for spec in SPORT_PASSPORT_SCHEMA]

# Map from column header to field spec
HEADER_TO_SPEC = {spec.column_header: spec for spec in SPORT_PASSPORT_SCHEMA}

# Map from internal name to field spec
NAME_TO_SPEC = {spec.name: spec for spec in SPORT_PASSPORT_SCHEMA}

# Index of the medical conditions field (for comma repair logic)
MEDICAL_CONDITIONS_INDEX = next(
    i for i, spec in enumerate(SPORT_PASSPORT_SCHEMA) 
    if spec.name == "medical_conditions"
)


def get_field_by_index(index: int) -> Optional[FieldSpec]:
    """Get field specification by column index."""
    if 0 <= index < len(SPORT_PASSPORT_SCHEMA):
        return SPORT_PASSPORT_SCHEMA[index]
    return None


def get_field_by_name(name: str) -> Optional[FieldSpec]:
    """Get field specification by internal name."""
    return NAME_TO_SPEC.get(name)


def get_required_fields() -> list[FieldSpec]:
    """Get list of all required fields."""
    return [spec for spec in SPORT_PASSPORT_SCHEMA if spec.required]


def get_display_name(spec: FieldSpec) -> str:
    """Get a clean display name for a field (without asterisk)."""
    return spec.column_header.rstrip('*')
