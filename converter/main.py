"""Main CLI entry point for Sport Passport CSV Converter."""

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .schema import (
    SPORT_PASSPORT_SCHEMA,
    COLUMN_HEADERS,
    EXPECTED_COLUMN_COUNT,
    get_display_name,
    get_required_fields,
    FieldType,
)
from .validator import Validator, ColumnMismatchError
from .corrector import Corrector
from .interactive import InteractiveCorrector, UserAbort, DefaultOverrides
from .row_detector import detect_rows_to_remove
from .column_variations import find_column_matches, get_field_display_name
from .banners import display_welcome_banner, display_step_separator, display_completion_banner


console = Console()


class SportPassportConverter:
    """Main converter class that orchestrates the conversion process."""
    
    def __init__(
        self, 
        input_path: str, 
        output_path: Optional[str] = None,
        auto_confirm: bool = False,
        default_postcode: Optional[str] = None,
        default_email: Optional[str] = None,
    ):
        self.input_path = Path(input_path)
        self.auto_confirm = auto_confirm
        
        # Pre-set default overrides from command line
        self.default_overrides = DefaultOverrides(
            postcode=default_postcode,
            email=default_email,
        )
        
        if output_path:
            self.output_path = Path(output_path)
        else:
            # Default output name
            self.output_path = self.input_path.with_suffix('.converted.csv')
        
        self.validator = Validator()
        self.corrector = Corrector()
        self.interactive = InteractiveCorrector()
        
        self.csv_repairs = 0
        self.rows_data: list[dict[str, Any]] = []
        # Track default values for fields that were added (not in input file)
        self.field_defaults: dict[str, str] = {}
        # Track all applied auto-corrections for log viewing
        self.applied_corrections: list = []
    
    def run(self) -> bool:
        """Run the full conversion process. Returns True on success."""
        try:
            # Display welcome banner
            display_welcome_banner()
            
            # Step 0: Prompt for default overrides (postcode/email)
            if not self.auto_confirm and not self.default_overrides.has_overrides:
                self.default_overrides = self.interactive.prompt_for_default_overrides()
            
            # Step 1: Load input file
            display_step_separator("LOADING INPUT FILE", 1)
            self.interactive.display_info(f"Loading {self.input_path}...")
            raw_data = self._load_input()
            
            if raw_data is None or len(raw_data) == 0:
                self.interactive.display_error("No data found in input file")
                return False
            
            self.interactive.display_success(f"Loaded {len(raw_data)} rows")
            
            # Step 2: Populate default values for fields that were added (not in input file)
            if self.field_defaults:
                for row in raw_data:
                    for field_name, default_value in self.field_defaults.items():
                        if field_name not in row or not row.get(field_name):
                            row[field_name] = default_value
            
            # Step 3: First pass - normalize and collect all auto-corrections
            display_step_separator("ANALYZING DATA", 3)
            self.interactive.display_info("Analyzing data and collecting corrections...")
            
            # Fields to skip validation for (will be overwritten by defaults)
            skip_validation_fields = set()
            if self.default_overrides.postcode:
                skip_validation_fields.add("postcode")
            if self.default_overrides.email:
                skip_validation_fields.add("email")
            # Also skip validation for fields that were added with defaults
            skip_validation_fields.update(self.field_defaults.keys())
            
            normalized_rows = []
            pending_auto_fixes: list[tuple[int, dict, list]] = []  # (idx, row, errors)
            
            for idx, row in enumerate(raw_data):
                # Normalize the row first
                normalized = self.corrector.normalize_row(idx, row)
                
                # Ensure default values are set for added fields
                for field_name, default_value in self.field_defaults.items():
                    if field_name not in normalized or not normalized.get(field_name):
                        normalized[field_name] = default_value
                
                # Validate (skipping fields that will be overwritten)
                result = self.validator.validate_row(idx, normalized)
                
                # Filter out errors for fields we'll override
                errors = [
                    e for e in result.errors 
                    if e.field_spec.name not in skip_validation_fields
                ]
                
                # Collect auto-fixable errors
                auto_fixable = [e for e in errors if e.is_auto_fixable]
                manual_required = [e for e in errors if not e.is_auto_fixable]
                
                normalized_rows.append(normalized)
                if auto_fixable or manual_required:
                    pending_auto_fixes.append((idx, normalized, errors))
            
            # Step 4: Review auto-corrections with user
            all_auto_corrections = []
            for idx, normalized, errors in pending_auto_fixes:
                for error in errors:
                    if error.is_auto_fixable and error.suggested_fix:
                        # Record the correction for review
                        from .corrector import CorrectionRecord
                        all_auto_corrections.append(CorrectionRecord(
                            row_index=error.row_index,
                            field_name=get_display_name(error.field_spec),
                            original_value=error.value,
                            corrected_value=error.suggested_fix,
                            correction_type=self._get_correction_type(error),
                        ))
            
            # Ask user to accept or reject auto-corrections
            if all_auto_corrections and not self.auto_confirm:
                display_step_separator("REVIEWING CORRECTIONS", 4)
            user_accepted_auto = True
            if all_auto_corrections and not self.auto_confirm:
                user_accepted_auto = self.interactive.prompt_review_auto_corrections(
                    all_auto_corrections, 
                    len(raw_data)
                )
            
            # Step 5: Apply corrections based on user choice
            # Only show banner if we actually have corrections to apply
            if pending_auto_fixes:
                display_step_separator("APPLYING CORRECTIONS", 5)
            valid_rows = []
            
            for idx, normalized in enumerate(normalized_rows):
                # Find pending fixes for this row
                pending = next(
                    (p for p in pending_auto_fixes if p[0] == idx), 
                    None
                )
                
                if pending is None:
                    # No issues with this row
                    valid_rows.append(normalized)
                    continue
                
                _, _, errors = pending
                
                # Filter out errors for fields we'll override
                errors = [
                    e for e in errors 
                    if e.field_spec.name not in skip_validation_fields
                ]
                
                if user_accepted_auto:
                    # Apply all auto-fixes
                    for error in errors:
                        if error.is_auto_fixable and error.suggested_fix:
                            normalized[error.field_spec.name] = error.suggested_fix
                            self.corrector.stats.total_corrections += 1
                            # Track applied correction for log
                            from .corrector import CorrectionRecord
                            self.applied_corrections.append(CorrectionRecord(
                                row_index=error.row_index,
                                field_name=get_display_name(error.field_spec),
                                original_value=error.value,
                                corrected_value=error.suggested_fix,
                                correction_type=self._get_correction_type(error),
                            ))
                    
                    # Handle remaining manual errors
                    manual_errors = [e for e in errors if not e.is_auto_fixable]
                    row_skipped = False
                    for error in manual_errors:
                        fixed = self.interactive.prompt_for_validation_error(
                            error, normalized
                        )
                        if fixed is not None:
                            normalized[error.field_spec.name] = fixed
                        else:
                            row_skipped = True
                            break
                    
                    if not row_skipped:
                        valid_rows.append(normalized)
                else:
                    # User rejected auto-corrections - manual review for everything
                    row_skipped = False
                    for error in errors:
                        fixed = self.interactive.prompt_for_validation_error(
                            error, normalized
                        )
                        if fixed is not None:
                            normalized[error.field_spec.name] = fixed
                        else:
                            row_skipped = True
                            break
                    
                    if not row_skipped:
                        valid_rows.append(normalized)
            
            # Step 6: Offer to view corrections log if any were applied
            if self.applied_corrections and not self.auto_confirm:
                self.interactive.prompt_view_corrections_log(self.applied_corrections)
            
            # Step 7: Display summary
            display_step_separator("SUMMARY", 7)
            self.interactive.display_summary(
                total_rows=len(raw_data),
                auto_corrections=self.corrector.get_summary(),
                csv_repairs=self.csv_repairs,
            )
            
            # Step 8: Review changes before export
            # Always show review prompt if there are changes (even in auto-confirm mode)
            total_changes = (len(self.applied_corrections) if self.applied_corrections else 0) + (len(self.interactive.manual_corrections) if self.interactive.manual_corrections else 0)
            if total_changes > 0:
                display_step_separator("REVIEWING CHANGES", 8)
            proceed_after_review = self.interactive.prompt_review_changes_before_export(
                self.applied_corrections,
                self.interactive.manual_corrections,
            )
            if not proceed_after_review:
                self.interactive.display_info("Export cancelled by user")
                return False
            
            # Step 9: Export
            display_step_separator("EXPORTING RESULTS", 9)
            if not valid_rows:
                self.interactive.display_error("No valid rows to export")
                display_completion_banner(success=False)
                return False
            
            # Filter out skipped rows
            valid_rows = [
                row for i, row in enumerate(valid_rows) 
                if i not in self.interactive.skipped_rows
            ]
            
            # Apply default overrides if set
            if self.default_overrides.has_overrides:
                valid_rows = self._apply_default_overrides(valid_rows)
            
            should_export = self.auto_confirm or self.interactive.confirm_export(
                str(self.output_path), len(valid_rows)
            )
            
            if should_export:
                self._export_csv(valid_rows)
                self.interactive.display_success(f"Exported to {self.output_path}")
                display_completion_banner(success=True)
                return True
            else:
                self.interactive.display_info("Export cancelled")
                display_completion_banner(success=False)
                return False
                
        except UserAbort as e:
            console.print()
            self.interactive.display_warning(f"Aborted: {e}")
            display_completion_banner(success=False)
            return False
        except KeyboardInterrupt:
            console.print()
            self.interactive.display_warning("Interrupted by user")
            display_completion_banner(success=False)
            return False
        except ValueError as e:
            # Check if this is a missing mandatory columns error
            if "Missing mandatory columns" in str(e):
                # Error already displayed in display_missing_mandatory_columns()
                display_completion_banner(success=False)
                return False
            # Other ValueError - display and exit
            console.print()
            self.interactive.display_error(f"Error: {e}")
            display_completion_banner(success=False)
            return False
        except Exception as e:
            console.print()
            self.interactive.display_error(f"Unexpected error: {e}")
            display_completion_banner(success=False)
            raise
    
    def _get_correction_type(self, error) -> str:
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
            return "case_normalization"
        elif "case" in error.error_message.lower():
            return "case_normalization"
        return "format"
    
    def _apply_default_overrides(
        self, 
        rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Apply default postcode and email values to all rows."""
        overrides_applied = []
        
        for row in rows:
            if self.default_overrides.postcode:
                row["postcode"] = self.default_overrides.postcode
            if self.default_overrides.email:
                row["email"] = self.default_overrides.email
            overrides_applied.append(row)
        
        # Log what was overridden
        if self.default_overrides.postcode:
            self.interactive.display_info(
                f"Applied default postcode '{self.default_overrides.postcode}' to {len(rows)} rows"
            )
        if self.default_overrides.email:
            self.interactive.display_info(
                f"Applied default email '{self.default_overrides.email}' to {len(rows)} rows"
            )
        
        return overrides_applied
    
    def _load_input(self) -> list[dict[str, Any]]:
        """Load input file (Excel or CSV)."""
        suffix = self.input_path.suffix.lower()
        
        if suffix in ('.xlsx', '.xls'):
            return self._load_excel()
        elif suffix == '.csv':
            return self._load_csv()
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
    
    def _load_excel(self) -> list[dict[str, Any]]:
        """Load data from Excel file."""
        # Read Excel file without assuming header row
        df = pd.read_excel(self.input_path, dtype=str, keep_default_na=False, header=None)
        
        # Detect header row and trailing rows
        header_row_idx, last_valid_row_idx = detect_rows_to_remove(df)
        
        # Default to first row if header not detected
        if header_row_idx is None:
            header_row_idx = 0
        
        # Prepare preview rows for user confirmation
        preview_top_rows = []
        preview_bottom_rows = []
        
        if header_row_idx > 0:
            # Get preview of rows to remove from top
            preview_top_rows = [
                df.iloc[i].values.tolist() 
                for i in range(min(5, header_row_idx))
            ]
        
        if last_valid_row_idx is not None and last_valid_row_idx < len(df) - 1:
            # Get preview of rows to remove from bottom
            start_idx = max(last_valid_row_idx + 1, len(df) - 5)
            preview_bottom_rows = [
                df.iloc[i].values.tolist() 
                for i in range(start_idx, len(df))
            ]
        
        # Ask user to confirm row removal
        if header_row_idx > 0 or (last_valid_row_idx is not None and last_valid_row_idx < len(df) - 1):
            if not self.auto_confirm:
                should_remove = self.interactive.prompt_confirm_row_removal(
                    header_row_idx,
                    last_valid_row_idx,
                    len(df),
                    preview_top_rows,
                    preview_bottom_rows,
                )
                
                if not should_remove:
                    # User chose not to remove rows, reset detection
                    header_row_idx = 0
                    last_valid_row_idx = None
            # If auto_confirm is True, proceed with removal
        
        # Remove rows from top if needed
        if header_row_idx > 0:
            df = df.iloc[header_row_idx:].reset_index(drop=True)
            # Adjust last_valid_row_idx after removing top rows
            if last_valid_row_idx is not None:
                last_valid_row_idx = last_valid_row_idx - header_row_idx
        
        # Remove rows from bottom if needed
        if last_valid_row_idx is not None and last_valid_row_idx < len(df) - 1:
            df = df.iloc[:last_valid_row_idx + 1].reset_index(drop=True)
        
        # Now treat first row as headers
        if len(df) == 0:
            return []
        
        headers = df.iloc[0].values.tolist()
        headers = [str(h).strip() if h is not None else "" for h in headers]
        
        # Use first row as headers, rest as data
        df.columns = headers
        df = df.iloc[1:].reset_index(drop=True)
        
        # Map column headers to internal names
        column_mapping = self._create_column_mapping(headers)
        
        if column_mapping is None:
            raise ValueError("Could not map Excel columns to expected schema")
        
        df = df.rename(columns=column_mapping)
        
        # Convert to list of dicts
        return df.to_dict('records')
    
    def _load_csv(self) -> list[dict[str, Any]]:
        """Load data from CSV file, handling malformed rows."""
        # Read all rows first for row detection
        all_rows = []
        with open(self.input_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            for row in reader:
                all_rows.append(row)
        
        if not all_rows:
            return []
        
        # Detect header row and trailing rows
        header_row_idx, last_valid_row_idx = detect_rows_to_remove(all_rows)
        
        # Default to first row if header not detected
        if header_row_idx is None:
            header_row_idx = 0
        
        # Prepare preview rows for user confirmation
        preview_top_rows = []
        preview_bottom_rows = []
        
        if header_row_idx > 0:
            # Get preview of rows to remove from top
            preview_top_rows = all_rows[:min(5, header_row_idx)]
        
        if last_valid_row_idx is not None and last_valid_row_idx < len(all_rows) - 1:
            # Get preview of rows to remove from bottom
            start_idx = max(last_valid_row_idx + 1, len(all_rows) - 5)
            preview_bottom_rows = all_rows[start_idx:]
        
        # Ask user to confirm row removal
        if header_row_idx > 0 or (last_valid_row_idx is not None and last_valid_row_idx < len(all_rows) - 1):
            if not self.auto_confirm:
                should_remove = self.interactive.prompt_confirm_row_removal(
                    header_row_idx,
                    last_valid_row_idx,
                    len(all_rows),
                    preview_top_rows,
                    preview_bottom_rows,
                )
                
                if not should_remove:
                    # User chose not to remove rows, reset detection
                    header_row_idx = 0
                    last_valid_row_idx = None
            # If auto_confirm is True, proceed with removal
        
        # Remove rows from top if needed
        if header_row_idx > 0:
            all_rows = all_rows[header_row_idx:]
            # Adjust last_valid_row_idx after removing top rows
            if last_valid_row_idx is not None:
                last_valid_row_idx = last_valid_row_idx - header_row_idx
        
        # Remove rows from bottom if needed
        if last_valid_row_idx is not None and last_valid_row_idx < len(all_rows) - 1:
            all_rows = all_rows[:last_valid_row_idx + 1]
        
        if not all_rows:
            return []
        
        # First row should be headers
        headers = all_rows[0]
        headers = [h.strip() if h else "" for h in headers]
        
        # Check if headers match expected
        column_mapping = self._create_column_mapping(headers)
        
        if column_mapping is None:
            raise ValueError("CSV headers do not match expected schema")
        
        # Process data rows
        rows = []
        for idx, raw_values in enumerate(all_rows[1:], start=0):
            # Check column count
            mismatch = self.validator.check_column_count(idx, raw_values)
            
            if mismatch:
                # Try auto-repair
                repaired = self.corrector.attempt_csv_repair(mismatch)
                
                if repaired:
                    self.csv_repairs += 1
                    raw_values = repaired
                else:
                    # Need manual intervention
                    repaired = self.interactive.prompt_for_column_mismatch(mismatch)
                    
                    if repaired:
                        self.csv_repairs += 1
                        raw_values = repaired
                    else:
                        # Row skipped
                        continue
            
            # Convert to dict using column mapping
            row_dict = {}
            for i, header in enumerate(headers):
                if i < len(raw_values):
                    internal_name = column_mapping.get(header)
                    if internal_name:
                        row_dict[internal_name] = raw_values[i]
            
            rows.append(row_dict)
        
        return rows
    
    def _create_column_mapping(self, headers: list[str]) -> Optional[dict[str, str]]:
        """Create mapping from file headers to internal field names."""
        mapping = {}
        
        # Clean headers
        cleaned_headers = [h.strip() for h in headers]
        
        # First pass: exact matches (including asterisk variations)
        exact_matches = {}
        for spec in SPORT_PASSPORT_SCHEMA:
            # Try exact match first
            if spec.column_header in cleaned_headers:
                exact_matches[spec.column_header] = spec.name
                mapping[spec.column_header] = spec.name
                continue
            
            # Try without asterisk
            header_no_star = spec.column_header.rstrip('*')
            for h in cleaned_headers:
                if h.rstrip('*') == header_no_star:
                    exact_matches[h] = spec.name
                    mapping[h] = spec.name
                    break
            else:
                # Try case-insensitive
                for h in cleaned_headers:
                    if h.lower().rstrip('*') == header_no_star.lower():
                        exact_matches[h] = spec.name
                        mapping[h] = spec.name
                        break
        
        # Second pass: use variation matching for unmatched headers
        unmatched_headers = [h for h in cleaned_headers if h and h not in mapping]
        if unmatched_headers:
            # Find matches using variation detection
            variation_matches = find_column_matches(unmatched_headers, min_confidence=0.5)
            
            # Filter out matches that conflict with already mapped fields
            mapped_field_names = set(mapping.values())
            confirmed_variations = {}
            
            for input_header, (field_name, confidence) in variation_matches.items():
                # Skip if this field is already mapped to a different header
                if field_name in mapped_field_names:
                    continue
                confirmed_variations[input_header] = (field_name, confidence)
            
            # If we found variation matches, ask user to confirm
            if confirmed_variations and not self.auto_confirm:
                user_confirmed = self.interactive.prompt_confirm_column_mappings(
                    confirmed_variations,
                    cleaned_headers,
                    mapping
                )
                # Add confirmed mappings
                mapping.update(user_confirmed)
            elif confirmed_variations and self.auto_confirm:
                # Auto-confirm: use all variation matches
                for input_header, (field_name, _) in confirmed_variations.items():
                    mapping[input_header] = field_name
            
            # Third pass: handle any remaining unmatched columns
            remaining_unmatched = [h for h in cleaned_headers if h and h not in mapping]
            if remaining_unmatched and not self.auto_confirm:
                # Prompt user to manually map unmatched columns
                # This may raise UserAbort if user chooses to exit
                manual_mappings = self.interactive.prompt_manual_column_mapping(
                    remaining_unmatched,
                    mapping
                )
                # Add manual mappings
                mapping.update(manual_mappings)
        
        # Handle default postcode/email when columns are missing
        found_names = set(mapping.values())
        
        # Check if postcode is missing but default is provided
        if "postcode" not in found_names and self.default_overrides.postcode:
            # Create a synthetic header name for the missing column
            synthetic_header = "__postcode_default__"
            mapping[synthetic_header] = "postcode"
            self.field_defaults["postcode"] = self.default_overrides.postcode
            if not self.auto_confirm:
                self.interactive.display_info(
                    f"Postcode column missing, but default postcode provided. "
                    f"Will use '{self.default_overrides.postcode}' for all rows."
                )
        
        # Check if email is missing but default is provided
        if "email" not in found_names and self.default_overrides.email:
            # Create a synthetic header name for the missing column
            synthetic_header = "__email_default__"
            mapping[synthetic_header] = "email"
            self.field_defaults["email"] = self.default_overrides.email
            if not self.auto_confirm:
                self.interactive.display_info(
                    f"Email column missing, but default email provided. "
                    f"Will use '{self.default_overrides.email}' for all rows."
                )
        
        # Recalculate found_names after adding defaults
        found_names = set(mapping.values())
        
        # Check for missing mandatory columns
        found_names = set(mapping.values())
        required_fields = get_required_fields()
        missing_mandatory_specs = []
        
        for spec in required_fields:
            if spec.name not in found_names:
                missing_mandatory_specs.append(spec)
        
        # If mandatory columns are missing, prompt user to add them with defaults
        if missing_mandatory_specs:
            # Get list of found columns for context
            found_columns = [h for h in cleaned_headers if h]
            
            # Generate fuzzy match suggestions for display
            suggestions = {}
            for spec in missing_mandatory_specs:
                suggestions[spec.column_header] = self._fuzzy_match_column(spec.column_header, cleaned_headers)
            
            # Display detailed report
            missing_column_names = [spec.column_header for spec in missing_mandatory_specs]
            self.interactive.display_missing_mandatory_columns(
                missing_column_names,
                found_columns,
                suggestions,
            )
            
            # Prompt for each missing mandatory field
            for spec in missing_mandatory_specs:
                field_name = spec.name
                field_display_name = get_display_name(spec)
                
                # Determine default value based on field type
                default_value = None
                if field_name == "classified_as_disabled":
                    default_value = "No"
                elif field_name == "postcode" and self.default_overrides.postcode:
                    default_value = self.default_overrides.postcode
                elif field_name == "email" and self.default_overrides.email:
                    default_value = self.default_overrides.email
                else:
                    # For other mandatory fields, we can't provide a sensible default
                    # Show error and exit
                    raise ValueError(
                        f"Missing mandatory field '{field_display_name}' with no default value. "
                        "Please update your input file to include this field."
                    )
                
                # Add field with default (prompt user if not auto_confirm)
                if default_value:
                    if self.auto_confirm:
                        # Auto-confirm: automatically add field with default
                        confirmed_default = default_value
                        self.interactive.display_info(
                            f"Missing mandatory field '{field_display_name}' - "
                            f"automatically adding with default value '{default_value}'"
                        )
                    else:
                        # Prompt user to add field with default
                        confirmed_default = self.interactive.prompt_add_missing_mandatory_field(
                            field_name,
                            field_display_name,
                            default_value,
                        )
                        
                        if confirmed_default is None:
                            # User declined to add the field
                            raise ValueError(
                                f"User declined to add missing mandatory field '{field_display_name}'. "
                                "Processing cannot continue."
                            )
                    
                    # Add field to mapping with synthetic header
                    synthetic_header = f"__{field_name}_default__"
                    mapping[synthetic_header] = field_name
                    self.field_defaults[field_name] = confirmed_default
        
        # Log missing optional columns (info only)
        optional_missing = []
        for spec in SPORT_PASSPORT_SCHEMA:
            if not spec.required and spec.name not in found_names:
                optional_missing.append(spec.column_header)
        
        if optional_missing:
            self.interactive.display_info(
                f"Optional columns not found (will be empty in output): {', '.join(optional_missing)}"
            )
        
        return mapping if mapping else None
    
    def _fuzzy_match_column(self, target: str, candidates: list[str], max_suggestions: int = 3) -> list[str]:
        """
        Find similar column names using simple fuzzy matching.
        
        Args:
            target: The column name we're looking for
            candidates: List of candidate column names to search
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            List of similar column names, sorted by similarity
        """
        target_lower = target.lower().rstrip('*').strip()
        target_words = set(target_lower.split())
        
        scores = []
        for candidate in candidates:
            if not candidate:
                continue
            
            candidate_lower = candidate.lower().strip()
            candidate_words = set(candidate_lower.split())
            
            # Calculate similarity score
            score = 0
            
            # Exact match (after normalization)
            if target_lower == candidate_lower:
                score = 100
            # Check for word overlap
            elif target_words and candidate_words:
                overlap = len(target_words & candidate_words)
                total_words = len(target_words | candidate_words)
                if total_words > 0:
                    score = (overlap / total_words) * 50
            
            # Check if one contains the other
            if target_lower in candidate_lower or candidate_lower in target_lower:
                score = max(score, 30)
            
            # Check character similarity (simple Levenshtein-like)
            if len(target_lower) > 0 and len(candidate_lower) > 0:
                common_chars = len(set(target_lower) & set(candidate_lower))
                total_chars = len(set(target_lower) | set(candidate_lower))
                if total_chars > 0:
                    char_score = (common_chars / total_chars) * 20
                    score = max(score, char_score)
            
            if score > 0:
                scores.append((score, candidate))
        
        # Sort by score (descending) and return top matches
        scores.sort(reverse=True, key=lambda x: x[0])
        return [candidate for score, candidate in scores[:max_suggestions] if score >= 15]
    
    def _export_csv(self, rows: list[dict[str, Any]]) -> None:
        """Export data to CSV with proper quoting."""
        with open(self.output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            
            # Write header
            writer.writerow(COLUMN_HEADERS)
            
            # Write data rows
            for row in rows:
                values = []
                for spec in SPORT_PASSPORT_SCHEMA:
                    value = row.get(spec.name, "")
                    values.append(value if value else "")
                writer.writerow(values)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert Excel spreadsheets to Sport Passport compliant CSV format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m converter input.xlsx
  python -m converter input.xlsx -o output.csv
  python -m converter data.csv -o cleaned.csv
  
  # Set default postcode and email for all rows:
  python -m converter input.xlsx --postcode "SW1A 1AA" --email "school@example.com"
        """,
    )
    
    parser.add_argument(
        "input",
        help="Input file (Excel .xlsx/.xls or CSV)",
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output CSV file path (default: input.converted.csv)",
    )
    
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Auto-confirm export without prompting",
    )
    
    parser.add_argument(
        "--postcode",
        help="Default postcode to apply to ALL rows (e.g., school postcode)",
    )
    
    parser.add_argument(
        "--email",
        help="Default email to apply to ALL rows (e.g., school contact email)",
    )
    
    args = parser.parse_args()
    
    # Check input file exists
    input_path = Path(args.input)
    if not input_path.exists():
        console.print(f"[red]Error:[/red] Input file not found: {args.input}")
        sys.exit(1)
    
    # Run converter
    converter = SportPassportConverter(
        args.input, 
        args.output, 
        auto_confirm=args.yes,
        default_postcode=args.postcode,
        default_email=args.email,
    )
    success = converter.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
