"""Column name variations and matching logic."""

from typing import Optional
import re

from .schema import SPORT_PASSPORT_SCHEMA, get_display_name


# Common variations for each field
COLUMN_VARIATIONS: dict[str, list[str]] = {
    "sport_passport_id": [
        "Sport Passport ID", "SportPassportID", "SPID", "ID", "Passport ID",
        "Sport Passport", "Passport Number"
    ],
    "first_name": [
        "First Name", "First Name*", "Firstname", "First", "FName", 
        "Given Name", "Forename", "Christian Name"
    ],
    "surname": [
        "Surname", "Surname*", "Last Name", "Last Name*", "LastName",
        "Family Name", "LName", "Second Name"
    ],
    "gender": [
        "Gender", "Gender*", "Sex", "Sex*"
    ],
    "classified_as_disabled": [
        "ClassifiedAsDisabled", "ClassifiedAsDisabled*", "Classified As Disabled",
        "Disabled", "Disability Status", "Has Disability"
    ],
    "medical_conditions": [
        "MedicalConditions", "Medical Conditions", "Medical Info",
        "Medical History", "Health Conditions", "Conditions"
    ],
    "date_of_birth": [
        "DateOfBirth", "DateOfBirth*", "Date of Birth", "Date of Birth*",
        "DOB", "DOB*", "Birth Date", "BirthDate", "Date Born"
    ],
    "address1": [
        "Address1", "Address 1", "Address Line 1", "Address", "Street Address",
        "Address Line One"
    ],
    "address2": [
        "Address2", "Address 2", "Address Line 2", "Address Line Two"
    ],
    "phone_number": [
        "PhoneNumber", "Phone Number", "Phone", "Telephone", "Tel",
        "Mobile", "Mobile Number", "Contact Number"
    ],
    "town_city": [
        "TownCity", "Town City", "Town", "City", "City/Town"
    ],
    "county": [
        "County", "State", "Region", "Province"
    ],
    "postcode": [
        "Postcode", "Postcode*", "Post Code", "Post Code*", "Postal Code",
        "Postal Code*", "Zip Code", "ZIP", "ZIP Code", "School Postcode",
        "School Postcode*", "School Post Code", "School Post Code*", "School Postal Code"
    ],
    "country": [
        "Country", "Nation"
    ],
    "emergency_contact_name": [
        "EmergencyContactName", "Emergency Contact Name", "Emergency Contact",
        "EC Name", "Emergency Name", "Contact Name"
    ],
    "emergency_contact_phone": [
        "EmergencyContactPhone", "Emergency Contact Phone", "EC Phone",
        "Emergency Phone", "Contact Phone", "Emergency Tel"
    ],
    "emergency_contact_phone2": [
        "EmergencyContactPhone2", "Emergency Contact Phone 2", "EC Phone 2",
        "Emergency Phone 2", "Contact Phone 2", "Alternative Emergency Phone"
    ],
    "email": [
        "Email", "Email*", "E-mail", "E-Mail", "Email Address",
        "Email Address*", "E-mail Address", "Mail", "Contact Email"
    ],
    "school_year": [
        "SchoolYear", "School Year", "Year", "Year Group", "Grade", "Form"
    ],
    "course_id": [
        "CourseID", "Course ID", "Course", "Course Number", "Course Code"
    ],
}


def normalize_column_name(name: str) -> str:
    """Normalize a column name for comparison."""
    # Remove asterisks, extra spaces, convert to lowercase
    normalized = name.strip().rstrip('*').lower()
    # Remove common punctuation
    normalized = re.sub(r'[_\-\s]+', ' ', normalized)
    return normalized.strip()


def find_best_match(
    input_header: str,
    field_name: str,
    variations: list[str]
) -> float:
    """
    Find the best match score for an input header against a field's variations.
    
    Returns a score between 0 and 1, where 1 is a perfect match.
    """
    input_normalized = normalize_column_name(input_header)
    
    # Check exact match (case-insensitive, ignoring asterisks and spaces)
    for variation in variations:
        var_normalized = normalize_column_name(variation)
        if input_normalized == var_normalized:
            return 1.0
    
    # Check if input contains variation or vice versa
    for variation in variations:
        var_normalized = normalize_column_name(variation)
        if input_normalized in var_normalized or var_normalized in input_normalized:
            # Partial match - score based on length similarity
            min_len = min(len(input_normalized), len(var_normalized))
            max_len = max(len(input_normalized), len(var_normalized))
            if max_len > 0:
                return min_len / max_len * 0.8
    
    # Check word overlap
    input_words = set(input_normalized.split())
    best_score = 0.0
    for variation in variations:
        var_normalized = normalize_column_name(variation)
        var_words = set(var_normalized.split())
        if input_words and var_words:
            overlap = len(input_words & var_words)
            total = len(input_words | var_words)
            if total > 0:
                score = overlap / total * 0.6
                best_score = max(best_score, score)
    
    return best_score


def find_column_matches(
    input_headers: list[str],
    min_confidence: float = 0.5
) -> dict[str, tuple[str, float]]:
    """
    Find matches between input headers and schema fields.
    
    Args:
        input_headers: List of column headers from input file
        min_confidence: Minimum confidence score to consider a match
        
    Returns:
        Dict mapping input header -> (field_name, confidence_score)
    """
    matches = {}
    
    for input_header in input_headers:
        if not input_header or not input_header.strip():
            continue
        
        best_match = None
        best_score = 0.0
        
        for spec in SPORT_PASSPORT_SCHEMA:
            field_name = spec.name
            variations = COLUMN_VARIATIONS.get(field_name, [])
            # Add the canonical header to variations
            variations = [spec.column_header] + variations
            
            score = find_best_match(input_header, field_name, variations)
            
            if score > best_score and score >= min_confidence:
                best_score = score
                best_match = field_name
        
        if best_match:
            matches[input_header] = (best_match, best_score)
    
    return matches


def get_field_display_name(field_name: str) -> str:
    """Get display name for a field."""
    for spec in SPORT_PASSPORT_SCHEMA:
        if spec.name == field_name:
            return get_display_name(spec)
    return field_name
