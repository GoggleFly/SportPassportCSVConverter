"""Test fixtures for Sport Passport CSV Converter tests."""

from pathlib import Path

FIXTURES_DIR = Path(__file__).parent

TEST_DATA_WITH_ERRORS = FIXTURES_DIR / "test_data_with_errors.csv"
TEST_DATA_COMMA_ISSUE = FIXTURES_DIR / "test_data_comma_issue.csv"
TEST_DATA_VALID = FIXTURES_DIR / "test_data_valid.csv"
TEST_DATA_WITH_EXTRA_ROWS = FIXTURES_DIR / "test_data_with_extra_rows.csv"
TEST_DATA_MISSING_MANDATORY = FIXTURES_DIR / "test_data_missing_mandatory.csv"
TEST_DATA_MISSING_OPTIONAL = FIXTURES_DIR / "test_data_missing_optional.csv"
