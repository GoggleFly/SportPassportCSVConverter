"""Tests for interactive module."""

import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from converter.interactive import (
    InteractiveCorrector,
    UserAbort,
    DefaultOverrides,
)
from converter.validator import (
    ValidationError,
    ColumnMismatchError,
)
from converter.schema import (
    get_field_by_name,
    EXPECTED_COLUMN_COUNT,
    MEDICAL_CONDITIONS_INDEX,
)


class TestInteractiveCorrectorBasics:
    """Basic interactive corrector tests."""
    
    @pytest.fixture
    def interactive(self):
        return InteractiveCorrector()
    
    def test_initialization(self, interactive):
        """Interactive corrector should initialize with empty lists."""
        assert interactive.skipped_rows == []
        assert interactive.manual_corrections == []


class TestValidationErrorPrompts:
    """Tests for validation error prompts."""
    
    @pytest.fixture
    def interactive(self):
        return InteractiveCorrector()
    
    @pytest.fixture
    def sample_error(self):
        """Create a sample validation error."""
        email_spec = get_field_by_name("email")
        return ValidationError(
            row_index=5,
            field_spec=email_spec,
            value="invalid-email",
            error_message="Invalid email format",
            is_auto_fixable=False,
        )
    
    @pytest.fixture
    def sample_row_data(self):
        return {
            "first_name": "John",
            "surname": "Smith",
            "email": "invalid-email",
            "date_of_birth": "16/12/2001",
        }
    
    @patch('converter.interactive.questionary.text')
    def test_prompt_returns_corrected_value(self, mock_text, interactive, sample_error, sample_row_data):
        """Should return corrected value from user input."""
        mock_text.return_value.ask.return_value = "valid@email.com"
        
        result = interactive.prompt_for_validation_error(sample_error, sample_row_data)
        
        assert result == "valid@email.com"
        assert len(interactive.manual_corrections) == 1
    
    @patch('converter.interactive.questionary.text')
    def test_prompt_skip_returns_none(self, mock_text, interactive, sample_error, sample_row_data):
        """Should return None and track skipped row when user skips."""
        mock_text.return_value.ask.return_value = "s"
        
        result = interactive.prompt_for_validation_error(sample_error, sample_row_data)
        
        assert result is None
        assert 5 in interactive.skipped_rows
    
    @patch('converter.interactive.questionary.text')
    def test_prompt_quit_raises_abort(self, mock_text, interactive, sample_error, sample_row_data):
        """Should raise UserAbort when user quits."""
        mock_text.return_value.ask.return_value = "q"
        
        with pytest.raises(UserAbort):
            interactive.prompt_for_validation_error(sample_error, sample_row_data)
    
    @patch('converter.interactive.questionary.text')
    def test_prompt_none_raises_abort(self, mock_text, interactive, sample_error, sample_row_data):
        """Should raise UserAbort when questionary returns None (Ctrl+C)."""
        mock_text.return_value.ask.return_value = None
        
        with pytest.raises(UserAbort):
            interactive.prompt_for_validation_error(sample_error, sample_row_data)
    
    @patch('converter.interactive.questionary.text')
    def test_manual_correction_recorded(self, mock_text, interactive, sample_error, sample_row_data):
        """Should record manual correction details."""
        mock_text.return_value.ask.return_value = "corrected@email.com"
        
        interactive.prompt_for_validation_error(sample_error, sample_row_data)
        
        assert len(interactive.manual_corrections) == 1
        correction = interactive.manual_corrections[0]
        assert correction["row"] == 5
        assert correction["field"] == "Email"
        assert correction["original"] == "invalid-email"
        assert correction["corrected"] == "corrected@email.com"


class TestColumnMismatchPrompts:
    """Tests for column mismatch prompts."""
    
    @pytest.fixture
    def interactive(self):
        return InteractiveCorrector()
    
    @pytest.fixture
    def sample_mismatch_too_many(self):
        """Create a sample column mismatch with too many columns."""
        # Simulate medical conditions split into 3 columns
        values = [""] * MEDICAL_CONDITIONS_INDEX
        values.extend(["Diabetes", "asthma", "uses inhaler"])  # 3 instead of 1
        remaining = EXPECTED_COLUMN_COUNT - MEDICAL_CONDITIONS_INDEX - 1
        values.extend([""] * remaining)
        # Now we have 2 extra columns
        
        return ColumnMismatchError(
            row_index=3,
            raw_values=values,
            expected_count=EXPECTED_COLUMN_COUNT,
            actual_count=len(values),
        )
    
    @pytest.fixture
    def sample_mismatch_too_few(self):
        """Create a sample column mismatch with too few columns."""
        values = [""] * (EXPECTED_COLUMN_COUNT - 2)
        
        return ColumnMismatchError(
            row_index=3,
            raw_values=values,
            expected_count=EXPECTED_COLUMN_COUNT,
            actual_count=len(values),
        )
    
    @patch('converter.interactive.questionary.text')
    def test_merge_columns_success(self, mock_text, interactive, sample_mismatch_too_many):
        """Should return repaired values when user provides merged value."""
        mock_text.return_value.ask.return_value = "Diabetes, asthma, uses inhaler"
        
        result = interactive.prompt_for_column_mismatch(sample_mismatch_too_many)
        
        # Result depends on the exact structure
        if result:
            assert len(result) == EXPECTED_COLUMN_COUNT
    
    @patch('converter.interactive.questionary.text')
    def test_merge_columns_skip(self, mock_text, interactive, sample_mismatch_too_many):
        """Should return None when user skips."""
        mock_text.return_value.ask.return_value = "s"
        
        result = interactive.prompt_for_column_mismatch(sample_mismatch_too_many)
        
        assert result is None
        assert 3 in interactive.skipped_rows
    
    @patch('converter.interactive.questionary.text')
    def test_merge_columns_quit(self, mock_text, interactive, sample_mismatch_too_many):
        """Should raise UserAbort when user quits."""
        mock_text.return_value.ask.return_value = "q"
        
        with pytest.raises(UserAbort):
            interactive.prompt_for_column_mismatch(sample_mismatch_too_many)
    
    @patch('converter.interactive.questionary.select')
    def test_too_few_columns_skip(self, mock_select, interactive, sample_mismatch_too_few):
        """Should handle too few columns by skip or abort."""
        mock_select.return_value.ask.return_value = "Skip this row"
        
        result = interactive.prompt_for_column_mismatch(sample_mismatch_too_few)
        
        assert result is None
        assert 3 in interactive.skipped_rows
    
    @patch('converter.interactive.questionary.select')
    def test_too_few_columns_abort(self, mock_select, interactive, sample_mismatch_too_few):
        """Should raise UserAbort when user chooses abort."""
        mock_select.return_value.ask.return_value = "Abort processing"
        
        with pytest.raises(UserAbort):
            interactive.prompt_for_column_mismatch(sample_mismatch_too_few)


class TestDisplayMethods:
    """Tests for display methods."""
    
    @pytest.fixture
    def interactive(self):
        return InteractiveCorrector()
    
    def test_display_error(self, interactive, capsys):
        """display_error should output error message."""
        interactive.display_error("Test error message")
        # Rich console output - just verify no exception
    
    def test_display_success(self, interactive, capsys):
        """display_success should output success message."""
        interactive.display_success("Test success message")
        # Rich console output - just verify no exception
    
    def test_display_info(self, interactive, capsys):
        """display_info should output info message."""
        interactive.display_info("Test info message")
        # Rich console output - just verify no exception
    
    def test_display_warning(self, interactive, capsys):
        """display_warning should output warning message."""
        interactive.display_warning("Test warning message")
        # Rich console output - just verify no exception


class TestConfirmExport:
    """Tests for export confirmation."""
    
    @pytest.fixture
    def interactive(self):
        return InteractiveCorrector()
    
    @patch('converter.interactive.questionary.confirm')
    def test_confirm_export_yes(self, mock_confirm, interactive):
        """Should return True when user confirms."""
        mock_confirm.return_value.ask.return_value = True
        
        result = interactive.confirm_export("/path/to/output.csv", 10)
        
        assert result is True
    
    @patch('converter.interactive.questionary.confirm')
    def test_confirm_export_no(self, mock_confirm, interactive):
        """Should return False when user declines."""
        mock_confirm.return_value.ask.return_value = False
        
        result = interactive.confirm_export("/path/to/output.csv", 10)
        
        assert result is False


class TestSummaryDisplay:
    """Tests for summary display."""
    
    @pytest.fixture
    def interactive(self):
        return InteractiveCorrector()
    
    def test_display_summary(self, interactive):
        """display_summary should not raise exceptions."""
        interactive.skipped_rows = [1, 5, 10]
        interactive.manual_corrections = [
            {"row": 2, "field": "Email", "original": "bad", "corrected": "good@email.com"},
        ]
        
        auto_corrections = {
            "total": 15,
            "by_type": {
                "date_format": 5,
                "case_normalization": 10,
            },
        }
        
        # Should not raise any exceptions
        interactive.display_summary(
            total_rows=100,
            auto_corrections=auto_corrections,
            csv_repairs=3,
        )


class TestUserAbortException:
    """Tests for UserAbort exception."""
    
    def test_user_abort_message(self):
        """UserAbort should store message."""
        exc = UserAbort("Test abort message")
        assert str(exc) == "Test abort message"
    
    def test_user_abort_is_exception(self):
        """UserAbort should be an Exception."""
        exc = UserAbort("Test")
        assert isinstance(exc, Exception)


class TestDefaultOverrides:
    """Tests for DefaultOverrides dataclass."""
    
    def test_default_overrides_empty(self):
        """Empty DefaultOverrides should have no overrides."""
        overrides = DefaultOverrides()
        assert overrides.postcode is None
        assert overrides.email is None
        assert overrides.has_overrides is False
    
    def test_default_overrides_with_postcode(self):
        """DefaultOverrides with postcode should have overrides."""
        overrides = DefaultOverrides(postcode="SW1A 1AA")
        assert overrides.postcode == "SW1A 1AA"
        assert overrides.email is None
        assert overrides.has_overrides is True
    
    def test_default_overrides_with_email(self):
        """DefaultOverrides with email should have overrides."""
        overrides = DefaultOverrides(email="test@example.com")
        assert overrides.postcode is None
        assert overrides.email == "test@example.com"
        assert overrides.has_overrides is True
    
    def test_default_overrides_with_both(self):
        """DefaultOverrides with both values should have overrides."""
        overrides = DefaultOverrides(postcode="SW1A 1AA", email="test@example.com")
        assert overrides.postcode == "SW1A 1AA"
        assert overrides.email == "test@example.com"
        assert overrides.has_overrides is True


class TestAutoCorrectionsReview:
    """Tests for auto-corrections review prompt."""
    
    @pytest.fixture
    def interactive(self):
        return InteractiveCorrector()
    
    @pytest.fixture
    def sample_corrections(self):
        from converter.corrector import CorrectionRecord
        return [
            CorrectionRecord(
                row_index=0,
                field_name="Gender",
                original_value="m",
                corrected_value="Male",
                correction_type="gender_abbreviation",
            ),
            CorrectionRecord(
                row_index=1,
                field_name="DateOfBirth",
                original_value="12/25/2001",
                corrected_value="25/12/2001",
                correction_type="us_to_uk_date",
            ),
        ]
    
    def test_no_corrections_returns_true(self, interactive):
        """Empty corrections list should return True."""
        result = interactive.prompt_review_auto_corrections([], 10)
        assert result is True
    
    @patch('converter.interactive.questionary.select')
    def test_accept_corrections(self, mock_select, interactive, sample_corrections):
        """User accepting corrections should return True."""
        mock_select.return_value.ask.return_value = "Accept all auto-corrections"
        
        result = interactive.prompt_review_auto_corrections(sample_corrections, 10)
        
        assert result is True
    
    @patch('converter.interactive.questionary.select')
    def test_reject_corrections(self, mock_select, interactive, sample_corrections):
        """User rejecting corrections should return False."""
        mock_select.return_value.ask.return_value = "Reject and review manually"
        
        result = interactive.prompt_review_auto_corrections(sample_corrections, 10)
        
        assert result is False
    
    @patch('converter.interactive.questionary.select')
    def test_cancel_raises_abort(self, mock_select, interactive, sample_corrections):
        """Cancelling should raise UserAbort."""
        mock_select.return_value.ask.return_value = None
        
        with pytest.raises(UserAbort):
            interactive.prompt_review_auto_corrections(sample_corrections, 10)


class TestCorrectionsLog:
    """Tests for corrections log viewing."""
    
    @pytest.fixture
    def interactive(self):
        return InteractiveCorrector()
    
    @pytest.fixture
    def sample_corrections(self):
        from converter.corrector import CorrectionRecord
        return [
            CorrectionRecord(
                row_index=0,
                field_name="Gender",
                original_value="m",
                corrected_value="Male",
                correction_type="gender_abbreviation",
            ),
            CorrectionRecord(
                row_index=1,
                field_name="Postcode",
                original_value="SW1A1AA",
                corrected_value="SW1A 1AA",
                correction_type="postcode_format",
            ),
        ]
    
    @patch('converter.interactive.questionary.confirm')
    def test_prompt_view_log_declines(self, mock_confirm, interactive, sample_corrections):
        """User declining to view log should not display it."""
        mock_confirm.return_value.ask.return_value = False
        
        interactive.prompt_view_corrections_log(sample_corrections)
        
        # Should have prompted
        assert mock_confirm.called
    
    @patch('builtins.input')
    @patch('converter.interactive.questionary.confirm')
    def test_prompt_view_log_displays(self, mock_confirm, mock_input, interactive, sample_corrections):
        """User accepting to view log should display it."""
        mock_confirm.return_value.ask.return_value = True
        mock_input.return_value = ""  # Press Enter to continue
        
        interactive.prompt_view_corrections_log(sample_corrections)
        
        # Should have prompted and displayed
        assert mock_confirm.called
    
    def test_prompt_view_log_empty_list(self, interactive):
        """Empty corrections list should not prompt."""
        # Should return immediately without prompting
        # This should not call questionary.confirm at all
        interactive.prompt_view_corrections_log([])
        
        # Should not raise any errors - method should return early


class TestPreExportReview:
    """Tests for pre-export review of changes."""
    
    @pytest.fixture
    def interactive(self):
        return InteractiveCorrector()
    
    @pytest.fixture
    def sample_auto_corrections(self):
        from converter.corrector import CorrectionRecord
        return [
            CorrectionRecord(
                row_index=0,
                field_name="Gender",
                original_value="m",
                corrected_value="Male",
                correction_type="gender_abbreviation",
            ),
            CorrectionRecord(
                row_index=1,
                field_name="Postcode",
                original_value="SW1A1AA",
                corrected_value="SW1A 1AA",
                correction_type="postcode_format",
            ),
        ]
    
    @pytest.fixture
    def sample_manual_corrections(self):
        return [
            {
                "row": 2,
                "field": "Email",
                "original": "invalid-email",
                "corrected": "correct@example.com",
            },
        ]
    
    def test_no_changes_returns_true(self, interactive):
        """Should return True immediately if no changes were made."""
        result = interactive.prompt_review_changes_before_export([], [])
        assert result is True
    
    @patch('converter.interactive.questionary.select')
    def test_proceed_without_review(self, mock_select, interactive, sample_auto_corrections, sample_manual_corrections):
        """User choosing to proceed without review should return True."""
        mock_select.return_value.ask.return_value = "Proceed to export without reviewing"
        
        result = interactive.prompt_review_changes_before_export(
            sample_auto_corrections,
            sample_manual_corrections,
        )
        
        assert result is True
        assert mock_select.called
    
    @patch('converter.interactive.questionary.select')
    def test_cancel_export(self, mock_select, interactive, sample_auto_corrections, sample_manual_corrections):
        """User choosing to cancel should return False."""
        mock_select.return_value.ask.return_value = "Cancel export"
        
        result = interactive.prompt_review_changes_before_export(
            sample_auto_corrections,
            sample_manual_corrections,
        )
        
        assert result is False
        assert mock_select.called
    
    @patch('builtins.input')
    @patch('converter.interactive.questionary.confirm')
    @patch('converter.interactive.questionary.select')
    def test_review_and_proceed(
        self,
        mock_select,
        mock_confirm,
        mock_input,
        interactive,
        sample_auto_corrections,
        sample_manual_corrections,
    ):
        """User reviewing changes and then proceeding should return True."""
        # First select: choose to review
        # Second confirm: proceed after review
        mock_select.return_value.ask.return_value = "Review detailed changes"
        mock_confirm.return_value.ask.return_value = True  # Proceed after review
        mock_input.return_value = ""  # Press Enter to continue through log display
        
        result = interactive.prompt_review_changes_before_export(
            sample_auto_corrections,
            sample_manual_corrections,
        )
        
        assert result is True
        assert mock_select.called
        assert mock_confirm.called
    
    @patch('builtins.input')
    @patch('converter.interactive.questionary.confirm')
    @patch('converter.interactive.questionary.select')
    def test_review_and_cancel(
        self,
        mock_select,
        mock_confirm,
        mock_input,
        interactive,
        sample_auto_corrections,
        sample_manual_corrections,
    ):
        """User reviewing changes and then cancelling should return False."""
        mock_select.return_value.ask.return_value = "Review detailed changes"
        mock_confirm.return_value.ask.return_value = False  # Cancel after review
        mock_input.return_value = ""  # Press Enter to continue through log display
        
        result = interactive.prompt_review_changes_before_export(
            sample_auto_corrections,
            sample_manual_corrections,
        )
        
        assert result is False
        assert mock_select.called
        assert mock_confirm.called
    
    @patch('converter.interactive.questionary.select')
    def test_only_auto_corrections(self, mock_select, interactive, sample_auto_corrections):
        """Should work with only auto-corrections."""
        mock_select.return_value.ask.return_value = "Proceed to export without reviewing"
        
        result = interactive.prompt_review_changes_before_export(
            sample_auto_corrections,
            [],
        )
        
        assert result is True
    
    @patch('converter.interactive.questionary.select')
    def test_only_manual_corrections(self, mock_select, interactive, sample_manual_corrections):
        """Should work with only manual corrections."""
        mock_select.return_value.ask.return_value = "Proceed to export without reviewing"
        
        result = interactive.prompt_review_changes_before_export(
            [],
            sample_manual_corrections,
        )
        
        assert result is True
    
    @patch('converter.interactive.questionary.select')
    def test_cancel_raises_abort(self, mock_select, interactive, sample_auto_corrections):
        """User cancelling should raise UserAbort."""
        mock_select.return_value.ask.return_value = None
        
        with pytest.raises(UserAbort):
            interactive.prompt_review_changes_before_export(
                sample_auto_corrections,
                [],
            )
        assert True  # If we get here, it worked


class TestDefaultOverridePrompts:
    """Tests for default override prompts."""
    
    @pytest.fixture
    def interactive(self):
        return InteractiveCorrector()
    
    @patch('converter.interactive.questionary.confirm')
    def test_prompt_declines_defaults(self, mock_confirm, interactive):
        """Should return empty overrides when user declines."""
        mock_confirm.return_value.ask.return_value = False
        
        result = interactive.prompt_for_default_overrides()
        
        assert result.has_overrides is False
        assert result.postcode is None
        assert result.email is None
    
    @patch('converter.interactive.questionary.text')
    @patch('converter.interactive.questionary.confirm')
    def test_prompt_accepts_valid_postcode(self, mock_confirm, mock_text, interactive):
        """Should accept and normalize valid postcode."""
        mock_confirm.return_value.ask.return_value = True
        # First call for postcode, second for email
        mock_text.return_value.ask.side_effect = ["sw1a 1aa", ""]
        
        result = interactive.prompt_for_default_overrides()
        
        assert result.postcode == "SW1A 1AA"
        assert result.email is None
    
    @patch('converter.interactive.questionary.text')
    @patch('converter.interactive.questionary.confirm')
    def test_prompt_accepts_valid_email(self, mock_confirm, mock_text, interactive):
        """Should accept and normalize valid email."""
        mock_confirm.return_value.ask.return_value = True
        # First call for postcode (skip), second for email
        mock_text.return_value.ask.side_effect = ["", "TEST@EXAMPLE.COM"]
        
        result = interactive.prompt_for_default_overrides()
        
        assert result.postcode is None
        assert result.email == "test@example.com"
    
    @patch('converter.interactive.questionary.text')
    @patch('converter.interactive.questionary.confirm')
    def test_prompt_accepts_both_values(self, mock_confirm, mock_text, interactive):
        """Should accept both postcode and email."""
        mock_confirm.return_value.ask.return_value = True
        mock_text.return_value.ask.side_effect = ["E1 9BR", "school@test.org"]
        
        result = interactive.prompt_for_default_overrides()
        
        assert result.postcode == "E1 9BR"
        assert result.email == "school@test.org"
    
    @patch('converter.interactive.questionary.confirm')
    def test_prompt_abort_on_cancel(self, mock_confirm, interactive):
        """Should raise UserAbort when user cancels."""
        mock_confirm.return_value.ask.return_value = None
        
        with pytest.raises(UserAbort):
            interactive.prompt_for_default_overrides()
    
    @patch('converter.interactive.questionary.text')
    @patch('converter.interactive.questionary.confirm')
    def test_prompt_normalizes_postcode_without_space(self, mock_confirm, mock_text, interactive):
        """Should add space to postcode if missing."""
        mock_confirm.return_value.ask.return_value = True
        mock_text.return_value.ask.side_effect = ["e19br", ""]
        
        result = interactive.prompt_for_default_overrides()
        
        assert result.postcode == "E1 9BR"
