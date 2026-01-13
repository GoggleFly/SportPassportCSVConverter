"""Interactive terminal interface for manual corrections."""

from dataclasses import dataclass
from typing import Any, Optional
import questionary
import re
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from .schema import (
    FieldSpec,
    SPORT_PASSPORT_SCHEMA,
    EXPECTED_COLUMN_COUNT,
    MEDICAL_CONDITIONS_INDEX,
    get_display_name,
    get_field_by_index,
)
from .column_variations import get_field_display_name
from .validator import ValidationError, ColumnMismatchError, RowValidationResult


console = Console()


class UserAbort(Exception):
    """Raised when user chooses to abort the process."""
    pass


@dataclass
class DefaultOverrides:
    """Default values to apply to all rows."""
    postcode: Optional[str] = None
    email: Optional[str] = None
    
    @property
    def has_overrides(self) -> bool:
        return self.postcode is not None or self.email is not None


class InteractiveCorrector:
    """Handles interactive prompts for manual data corrections."""
    
    # UK Postcode regex pattern for validation
    UK_POSTCODE_PATTERN = re.compile(r'^[A-Z]{1,2}[0-9][0-9A-Z]?\s*[0-9][A-Z]{2}$', re.IGNORECASE)
    # Email regex pattern for validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    def __init__(self):
        self.skipped_rows: list[int] = []
        self.manual_corrections: list[dict] = []
    
    def prompt_for_default_overrides(self) -> DefaultOverrides:
        """
        Prompt user if they want to provide default values for postcode and email.
        These will be applied to ALL rows in the output.
        
        Returns DefaultOverrides with any values the user provides.
        """
        console.print()
        console.print(Panel.fit(
            "[bold]Default Value Override[/bold]\n\n"
            "Schools often use a standard postcode and email for all members.\n"
            "You can set default values that will be applied to ALL rows.",
            border_style="cyan",
        ))
        console.print()
        
        overrides = DefaultOverrides()
        
        # Ask if user wants to set defaults
        set_defaults = questionary.confirm(
            "Would you like to set default values for Postcode and Email?",
            default=False,
        ).ask()
        
        if set_defaults is None:
            raise UserAbort("User cancelled")
        
        if not set_defaults:
            return overrides
        
        # Prompt for postcode
        console.print()
        while True:
            postcode = questionary.text(
                "Enter default Postcode (e.g., SW1A 1AA) or press Enter to skip:",
                default="",
            ).ask()
            
            if postcode is None:
                raise UserAbort("User cancelled")
            
            if not postcode.strip():
                break
            
            # Normalize and validate
            normalized = postcode.strip().upper()
            # Add space if missing
            if ' ' not in normalized and len(normalized) >= 5:
                normalized = normalized[:-3] + ' ' + normalized[-3:]
            
            if self.UK_POSTCODE_PATTERN.match(normalized):
                overrides.postcode = normalized
                self.display_success(f"Default postcode set: {normalized}")
                break
            else:
                self.display_error(f"Invalid UK postcode format: {postcode}")
                self.display_info("Please enter a valid UK postcode (e.g., SW1A 1AA)")
        
        # Prompt for email
        console.print()
        while True:
            email = questionary.text(
                "Enter default Email address or press Enter to skip:",
                default="",
            ).ask()
            
            if email is None:
                raise UserAbort("User cancelled")
            
            if not email.strip():
                break
            
            # Normalize and validate
            normalized = email.strip().lower()
            
            if self.EMAIL_PATTERN.match(normalized):
                overrides.email = normalized
                self.display_success(f"Default email set: {normalized}")
                break
            else:
                self.display_error(f"Invalid email format: {email}")
                self.display_info("Please enter a valid email address")
        
        if overrides.has_overrides:
            console.print()
            self.display_info("Default values will be applied to ALL rows in the output.")
        
        return overrides
    
    def prompt_for_validation_error(
        self,
        error: ValidationError,
        row_data: dict[str, Any],
    ) -> Optional[str]:
        """
        Prompt user to fix a validation error.
        
        Returns corrected value, or None if row should be skipped.
        Raises UserAbort if user wants to abort.
        """
        # Build context display
        self._display_validation_error_context(error, row_data)
        
        # Prompt for correction
        result = questionary.text(
            f"Enter corrected value (or 's' to skip row, 'q' to quit):",
            default=str(error.value) if error.value else "",
        ).ask()
        
        if result is None or result.lower() == 'q':
            raise UserAbort("User chose to abort")
        
        if result.lower() == 's':
            self.skipped_rows.append(error.row_index)
            return None
        
        self.manual_corrections.append({
            "row": error.row_index,
            "field": get_display_name(error.field_spec),
            "original": error.value,
            "corrected": result,
        })
        
        return result
    
    def _display_validation_error_context(
        self,
        error: ValidationError,
        row_data: dict[str, Any],
    ) -> None:
        """Display context for a validation error."""
        console.print()
        
        # Header
        title = f"Row {error.row_index + 2}: Validation Error"  # +2 for 1-based + header
        
        # Build info table
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        table.add_column("Label", style="cyan")
        table.add_column("Value")
        
        # Add name for context
        first_name = row_data.get("first_name", "")
        surname = row_data.get("surname", "")
        if first_name or surname:
            table.add_row("Name:", f"{first_name} {surname}".strip())
        
        # Add a few other fields for context
        if row_data.get("email"):
            table.add_row("Email:", str(row_data.get("email")))
        if row_data.get("date_of_birth"):
            table.add_row("DOB:", str(row_data.get("date_of_birth")))
        
        # Separator and error info
        error_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        error_table.add_column("Label", style="yellow")
        error_table.add_column("Value", style="red")
        
        error_table.add_row("⚠ Issue:", error.error_message)
        error_table.add_row("Field:", get_display_name(error.field_spec))
        error_table.add_row("Current:", str(error.value) if error.value else "(empty)")
        
        # Show allowed values if applicable
        if error.field_spec.allowed_values:
            allowed = ", ".join(error.field_spec.allowed_values)
            error_table.add_row("Allowed:", allowed)
        
        # Create panel
        content = Table.grid()
        content.add_row(table)
        content.add_row(Text(""))
        content.add_row(error_table)
        
        panel = Panel(
            content,
            title=title,
            title_align="left",
            border_style="yellow",
        )
        console.print(panel)
    
    def prompt_for_column_mismatch(
        self,
        error: ColumnMismatchError,
    ) -> Optional[list[str]]:
        """
        Prompt user to repair a row with wrong column count.
        
        Returns repaired values list, or None if row should be skipped.
        Raises UserAbort if user wants to abort.
        """
        self._display_column_mismatch_context(error)
        
        # If too many columns, likely medical conditions issue
        if error.actual_count > error.expected_count:
            return self._prompt_merge_columns(error)
        else:
            # Too few columns - ask user what to do
            console.print(
                f"[yellow]Row has {error.actual_count} columns but {error.expected_count} expected.[/yellow]"
            )
            console.print("[dim]This row cannot be automatically repaired.[/dim]")
            
            result = questionary.select(
                "What would you like to do?",
                choices=[
                    "Skip this row",
                    "Abort processing",
                ],
            ).ask()
            
            if result is None or result == "Abort processing":
                raise UserAbort("User chose to abort")
            
            self.skipped_rows.append(error.row_index)
            return None
    
    def _display_column_mismatch_context(self, error: ColumnMismatchError) -> None:
        """Display context for a column count mismatch."""
        console.print()
        
        title = f"Row {error.row_index + 2}: Column Count Mismatch"
        subtitle = f"Found {error.actual_count} columns, expected {error.expected_count}"
        
        # Try to show name if we can parse it
        name = ""
        if len(error.raw_values) > 2:
            name = f"{error.raw_values[1]} {error.raw_values[2]}".strip()
        
        # Build table showing the problematic area
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        table.add_column("Info", style="cyan")
        table.add_column("Value")
        
        if name:
            table.add_row("Name:", name)
        table.add_row("Issue:", subtitle)
        
        panel = Panel(
            table,
            title=title,
            title_align="left",
            border_style="red",
        )
        console.print(panel)
    
    def _prompt_merge_columns(self, error: ColumnMismatchError) -> Optional[list[str]]:
        """Prompt user to merge columns for comma-split repair."""
        extra = error.extra_columns
        values = error.raw_values
        med_idx = MEDICAL_CONDITIONS_INDEX
        
        # Show the columns around the likely problem area
        console.print()
        console.print("[bold]Raw data around MedicalConditions field:[/bold]")
        
        table = Table(show_header=True, box=box.ROUNDED)
        table.add_column("Col #", style="dim")
        table.add_column("Expected Field", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Note", style="yellow")
        
        # Show columns from before medical conditions to after the extra ones
        start = max(0, med_idx - 1)
        end = min(len(values), med_idx + extra + 3)
        
        for i in range(start, end):
            expected_field = get_field_by_index(i)
            field_name = get_display_name(expected_field) if expected_field else "?"
            
            value = values[i] if i < len(values) else ""
            
            # Add note for likely merged area
            note = ""
            if i == med_idx:
                note = "← MedicalConditions start"
            elif med_idx < i <= med_idx + extra:
                note = "← likely part of MedicalConditions"
            elif i == med_idx + extra + 1:
                note = "← likely Address1?"
            
            table.add_row(f"[{i}]", field_name, value[:50] + ("..." if len(value) > 50 else ""), note)
        
        console.print(table)
        console.print()
        
        # Ask user to provide the correct medical conditions value
        console.print("[bold]The above columns were likely split incorrectly due to commas in MedicalConditions.[/bold]")
        console.print("[dim]Please enter the complete MedicalConditions text (commas are OK).[/dim]")
        console.print()
        
        # Pre-fill with merged values as suggestion
        suggested = ", ".join(values[med_idx:med_idx + extra + 1])
        
        result = questionary.text(
            "MedicalConditions value (or 's' to skip row, 'q' to quit):",
            default=suggested,
        ).ask()
        
        if result is None or result.lower() == 'q':
            raise UserAbort("User chose to abort")
        
        if result.lower() == 's':
            self.skipped_rows.append(error.row_index)
            return None
        
        # Build repaired row
        repaired = values[:med_idx]
        repaired.append(result)
        repaired.extend(values[med_idx + extra + 1:])
        
        if len(repaired) != error.expected_count:
            console.print(f"[red]Repair resulted in {len(repaired)} columns, still not {error.expected_count}.[/red]")
            console.print("[dim]You may need to manually edit this row in the source file.[/dim]")
            
            skip = questionary.confirm("Skip this row?", default=True).ask()
            if skip:
                self.skipped_rows.append(error.row_index)
                return None
            raise UserAbort("Cannot repair row")
        
        self.manual_corrections.append({
            "row": error.row_index,
            "field": "MedicalConditions",
            "original": f"(split into {extra + 1} columns)",
            "corrected": result,
        })
        
        return repaired
    
    def display_progress(self, current: int, total: int, message: str = "") -> None:
        """Display progress indicator."""
        console.print(f"[dim]Processing row {current}/{total}... {message}[/dim]", end="\r")
    
    def prompt_review_auto_corrections(
        self,
        corrections: list,
        total_rows: int,
    ) -> bool:
        """
        Display auto-corrections and ask user to accept or reject.
        
        Returns True if user accepts, False if user wants manual review.
        """
        if not corrections:
            return True  # Nothing to review
        
        console.print()
        console.print(Panel.fit(
            f"[bold yellow]Auto-Corrections Review[/bold yellow]\n\n"
            f"The following {len(corrections)} correction(s) will be applied automatically.",
            border_style="yellow",
        ))
        console.print()
        
        # Group corrections by type for cleaner display
        by_type: dict[str, list] = {}
        for corr in corrections:
            corr_type = corr.correction_type
            if corr_type not in by_type:
                by_type[corr_type] = []
            by_type[corr_type].append(corr)
        
        # Display corrections by type
        for corr_type, corr_list in by_type.items():
            type_label = corr_type.replace("_", " ").title()
            console.print(f"[bold cyan]{type_label}[/bold cyan] ({len(corr_list)} corrections)")
            
            table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
            table.add_column("Row", style="dim", width=5)
            table.add_column("Field", style="cyan", width=20)
            table.add_column("Original", style="red", width=25)
            table.add_column("Corrected", style="green", width=25)
            
            # Show up to 10 examples per type
            for corr in corr_list[:10]:
                table.add_row(
                    str(corr.row_index + 2),  # +2 for 1-based + header
                    corr.field_name,
                    str(corr.original_value)[:25],
                    str(corr.corrected_value)[:25],
                )
            
            if len(corr_list) > 10:
                table.add_row("...", f"({len(corr_list) - 10} more)", "", "")
            
            console.print(table)
            console.print()
        
        # Ask for confirmation
        console.print("[bold]Would you like to:[/bold]")
        console.print("  [green]Accept[/green] - Apply all auto-corrections and proceed")
        console.print("  [yellow]Reject[/yellow] - Review each correction manually")
        console.print()
        
        result = questionary.select(
            "Choose an option:",
            choices=[
                "Accept all auto-corrections",
                "Reject and review manually",
            ],
        ).ask()
        
        if result is None:
            raise UserAbort("User cancelled")
        
        return result == "Accept all auto-corrections"
    
    def prompt_view_corrections_log(
        self,
        corrections: list,
    ) -> None:
        """
        Prompt user if they want to view the full log of applied corrections.
        
        Args:
            corrections: List of CorrectionRecord objects that were applied
        """
        if not corrections:
            return
        
        console.print()
        view_log = questionary.confirm(
            f"Would you like to view the full log of {len(corrections)} applied correction(s)?",
            default=False,
        ).ask()
        
        if view_log is None:
            raise UserAbort("User cancelled")
        
        if view_log:
            self.display_corrections_log(corrections)
    
    def display_corrections_log(
        self,
        corrections: list,
    ) -> None:
        """
        Display a detailed log of all applied corrections.
        
        Args:
            corrections: List of CorrectionRecord objects
        """
        console.print()
        console.print(Panel.fit(
            f"[bold cyan]Auto-Corrections Log[/bold cyan]\n\n"
            f"Complete log of {len(corrections)} correction(s) that were applied.",
            border_style="cyan",
        ))
        console.print()
        
        # Group corrections by type for cleaner display
        by_type: dict[str, list] = {}
        for corr in corrections:
            corr_type = corr.correction_type
            if corr_type not in by_type:
                by_type[corr_type] = []
            by_type[corr_type].append(corr)
        
        # Display corrections by type
        for corr_type, corr_list in by_type.items():
            type_label = corr_type.replace("_", " ").title()
            console.print(f"[bold cyan]{type_label}[/bold cyan] ({len(corr_list)} corrections)")
            
            table = Table(show_header=True, box=box.ROUNDED, padding=(0, 1))
            table.add_column("Row", style="dim", width=6, justify="right")
            table.add_column("Field", style="cyan", width=25)
            table.add_column("Original Value", style="red", width=30)
            table.add_column("Corrected Value", style="green", width=30)
            
            # Sort by row index for easier reading
            corr_list_sorted = sorted(corr_list, key=lambda x: x.row_index)
            
            for corr in corr_list_sorted:
                table.add_row(
                    str(corr.row_index + 2),  # +2 for 1-based + header
                    corr.field_name,
                    str(corr.original_value),
                    str(corr.corrected_value),
                )
            
            console.print(table)
            console.print()
        
        # Wait for user to continue
        console.print("[dim]Press Enter to continue...[/dim]")
        input()
        console.print()
    
    def prompt_review_changes_before_export(
        self,
        applied_corrections: list,
        manual_corrections: list,
    ) -> bool:
        """
        Prompt user to review all changes before final export.
        
        This is called after all corrections have been applied and summary displayed,
        but before the final export confirmation.
        
        Args:
            applied_corrections: List of CorrectionRecord objects (auto-corrections)
            manual_corrections: List of dicts with manual correction info
            
        Returns:
            True if user wants to proceed with export, False to cancel
        """
        total_auto = len(applied_corrections) if applied_corrections else 0
        total_manual = len(manual_corrections) if manual_corrections else 0
        total_changes = total_auto + total_manual
        
        # If no changes were made, skip the review
        if total_changes == 0:
            return True
        
        console.print()
        console.print(Panel.fit(
            "[bold yellow]Review Changes Before Export[/bold yellow]\n\n"
            f"Before generating the final output, you can review all {total_changes} change(s) that were made:\n"
            f"  • {total_auto} auto-correction(s)\n"
            f"  • {total_manual} manual correction(s)",
            border_style="yellow",
        ))
        console.print()
        
        choices = [
            "Proceed to export without reviewing",
            "Review detailed changes",
            "Cancel export",
        ]
        
        result = questionary.select(
            "Would you like to review the changes before export?",
            choices=choices,
        ).ask()
        
        if result is None:
            raise UserAbort("User cancelled")
        
        if result == "Cancel export":
            console.print()
            console.print("[yellow]Export cancelled by user.[/yellow]")
            return False
        
        if result == "Review detailed changes":
            console.print()
            # Show auto-corrections if any
            if applied_corrections:
                console.print(Panel.fit(
                    "[bold cyan]Auto-Corrections Applied[/bold cyan]\n\n"
                    f"{total_auto} automatic correction(s) were applied to your data.",
                    border_style="cyan",
                ))
                console.print()
                self.display_corrections_log(applied_corrections)
            
            # Show manual corrections if any
            if manual_corrections:
                console.print()
                console.print(Panel.fit(
                    "[bold green]Manual Corrections[/bold green]\n\n"
                    f"{total_manual} manual correction(s) were made during interactive review.",
                    border_style="green",
                ))
                console.print()
                
                table = Table(show_header=True, box=box.ROUNDED, padding=(0, 1))
                table.add_column("Row", style="dim", width=6, justify="right")
                table.add_column("Field", style="cyan", width=25)
                table.add_column("Original Value", style="red", width=30)
                table.add_column("Corrected Value", style="green", width=30)
                
                # Sort by row index
                manual_sorted = sorted(manual_corrections, key=lambda x: x.get("row", 0))
                
                for corr in manual_sorted:
                    row_num = str(corr.get("row", 0) + 2)  # +2 for 1-based + header
                    field = corr.get("field", "Unknown")
                    original = str(corr.get("original", ""))
                    corrected = str(corr.get("corrected", ""))
                    
                    table.add_row(row_num, field, original, corrected)
                
                console.print(table)
                console.print()
                
                # Wait for user to continue
                console.print("[dim]Press Enter to continue...[/dim]")
                input()
                console.print()
            
            # After review, ask again if they want to proceed
            console.print()
            proceed = questionary.confirm(
                "Proceed with export after reviewing changes?",
                default=True,
            ).ask()
            
            if proceed is None:
                raise UserAbort("User cancelled")
            
            if not proceed:
                console.print()
                console.print("[yellow]Export cancelled by user.[/yellow]")
                return False
        
        # User chose to proceed without reviewing
        return True
    
    def display_summary(
        self,
        total_rows: int,
        auto_corrections: dict,
        csv_repairs: int,
    ) -> None:
        """Display final processing summary."""
        console.print()
        console.print()
        
        # Header
        console.print(Panel.fit(
            "[bold green]Processing Complete[/bold green]",
            border_style="green",
        ))
        console.print()
        
        # Stats table
        table = Table(title="Summary", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="white", justify="right")
        
        table.add_row("Total rows processed", str(total_rows))
        table.add_row("Rows skipped", str(len(self.skipped_rows)))
        table.add_row("Auto-corrections applied", str(auto_corrections.get("total", 0)))
        table.add_row("CSV comma repairs", str(csv_repairs))
        table.add_row("Manual corrections", str(len(self.manual_corrections)))
        
        console.print(table)
        
        # Show correction breakdown if any
        if auto_corrections.get("by_type"):
            console.print()
            type_table = Table(title="Auto-corrections by Type", box=box.SIMPLE)
            type_table.add_column("Type", style="cyan")
            type_table.add_column("Count", justify="right")
            
            for corr_type, count in auto_corrections["by_type"].items():
                type_table.add_row(corr_type, str(count))
            
            console.print(type_table)
        
        if self.skipped_rows:
            console.print()
            console.print(f"[yellow]Skipped rows: {', '.join(str(r + 2) for r in self.skipped_rows)}[/yellow]")
    
    def prompt_confirm_row_removal(
        self,
        header_row_idx: Optional[int],
        last_valid_row_idx: Optional[int],
        total_rows: int,
        preview_top_rows: list[list[str]],
        preview_bottom_rows: list[list[str]],
    ) -> bool:
        """
        Display detected rows to remove and ask for user confirmation.
        
        Args:
            header_row_idx: Index of header row (rows before this will be removed)
            last_valid_row_idx: Index of last valid row (rows after this will be removed)
            total_rows: Total number of rows in file
            preview_top_rows: Preview of rows that will be removed from top
            preview_bottom_rows: Preview of rows that will be removed from bottom
            
        Returns:
            True if user confirms removal, False otherwise
        """
        console.print()
        console.print(Panel.fit(
            "[bold yellow]Row Detection[/bold yellow]\n\n"
            "The utility has detected rows that may be metadata or summary rows.",
            border_style="yellow",
        ))
        console.print()
        
        rows_to_remove_top = header_row_idx if header_row_idx and header_row_idx > 0 else 0
        rows_to_remove_bottom = (
            (total_rows - 1 - last_valid_row_idx) 
            if last_valid_row_idx is not None and last_valid_row_idx < total_rows - 1 
            else 0
        )
        total_to_remove = rows_to_remove_top + rows_to_remove_bottom
        
        if total_to_remove == 0:
            return False
        
        # Show summary
        info_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        info_table.add_column("Info", style="cyan")
        info_table.add_column("Value")
        
        info_table.add_row("Total rows in file:", str(total_rows))
        if rows_to_remove_top > 0:
            info_table.add_row("Rows to remove from top:", f"{rows_to_remove_top} (rows 1-{rows_to_remove_top})")
        if rows_to_remove_bottom > 0:
            info_table.add_row("Rows to remove from bottom:", f"{rows_to_remove_bottom} (rows {last_valid_row_idx + 2}-{total_rows})")
        info_table.add_row("Rows to keep:", str(total_rows - total_to_remove))
        
        console.print(info_table)
        console.print()
        
        # Show preview of rows to remove from top
        if rows_to_remove_top > 0 and preview_top_rows:
            console.print("[bold]Preview of rows to remove from top:[/bold]")
            preview_table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
            preview_table.add_column("Row #", style="dim", width=6)
            preview_table.add_column("Preview", style="yellow", width=70)
            
            for i, row in enumerate(preview_top_rows[:5]):
                preview_text = " | ".join(str(cell)[:20] for cell in row[:5] if cell)
                if len(preview_text) > 70:
                    preview_text = preview_text[:67] + "..."
                preview_table.add_row(str(i + 1), preview_text)
            
            if rows_to_remove_top > 5:
                preview_table.add_row("...", f"({rows_to_remove_top - 5} more rows)")
            
            console.print(preview_table)
            console.print()
        
        # Show preview of rows to remove from bottom
        if rows_to_remove_bottom > 0 and preview_bottom_rows:
            console.print("[bold]Preview of rows to remove from bottom:[/bold]")
            preview_table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
            preview_table.add_column("Row #", style="dim", width=6)
            preview_table.add_column("Preview", style="yellow", width=70)
            
            start_row_num = last_valid_row_idx + 2 if last_valid_row_idx is not None else total_rows - len(preview_bottom_rows) + 1
            for i, row in enumerate(preview_bottom_rows[:5]):
                preview_text = " | ".join(str(cell)[:20] for cell in row[:5] if cell)
                if len(preview_text) > 70:
                    preview_text = preview_text[:67] + "..."
                preview_table.add_row(str(start_row_num + i), preview_text)
            
            if rows_to_remove_bottom > 5:
                preview_table.add_row("...", f"({rows_to_remove_bottom - 5} more rows)")
            
            console.print(preview_table)
            console.print()
        
        # Ask for confirmation
        result = questionary.select(
            "Would you like to remove these rows?",
            choices=[
                "Yes, remove these rows",
                "No, keep all rows",
            ],
        ).ask()
        
        if result is None:
            raise UserAbort("User cancelled")
        
        return result == "Yes, remove these rows"
    
    def display_missing_mandatory_columns(
        self,
        missing_columns: list[str],
        found_columns: list[str],
        suggestions: Optional[dict[str, list[str]]] = None,
    ) -> None:
        """
        Display detailed report of missing mandatory columns.
        
        Args:
            missing_columns: List of missing mandatory column names
            found_columns: List of columns that were found
            suggestions: Optional dict mapping missing columns to suggested similar column names
        """
        console.print()
        console.print(Panel.fit(
            "[bold red]Missing Mandatory Columns[/bold red]\n\n"
            "The input file is missing one or more required columns. "
            "Processing cannot continue.",
            border_style="red",
        ))
        console.print()
        
        # Show missing columns
        missing_table = Table(title="Missing Mandatory Columns", box=box.ROUNDED)
        missing_table.add_column("Column Name", style="red")
        missing_table.add_column("Status", style="red")
        
        for col in missing_columns:
            missing_table.add_row(col, "REQUIRED - Missing")
        
        console.print(missing_table)
        console.print()
        
        # Show found columns for context
        if found_columns:
            found_table = Table(title="Columns Found in File", box=box.SIMPLE)
            found_table.add_column("Column Name", style="green")
            
            for col in found_columns[:20]:  # Show first 20
                found_table.add_row(col)
            
            if len(found_columns) > 20:
                found_table.add_row(f"... ({len(found_columns) - 20} more columns)")
            
            console.print(found_table)
            console.print()
        
        # Show suggestions if available and there are actual suggestions
        has_suggestions = False
        if suggestions:
            for suggested in suggestions.values():
                if suggested:  # Check if any suggestions exist
                    has_suggestions = True
                    break
        
        if has_suggestions:
            console.print("[bold yellow]Suggestions:[/bold yellow]")
            console.print("The following columns in your file might match the missing columns:")
            console.print()
            
            for missing_col, suggested in suggestions.items():
                if suggested:
                    console.print(f"  [cyan]{missing_col}[/cyan] might be:")
                    for sug in suggested[:3]:  # Show top 3 suggestions
                        console.print(f"    - {sug}")
                    console.print()
        
        console.print("[bold]Please update your input file to include all mandatory columns.[/bold]")
        console.print()
    
    def prompt_add_missing_mandatory_field(
        self,
        field_name: str,
        field_display_name: str,
        default_value: str,
    ) -> Optional[str]:
        """
        Prompt user to add a missing mandatory field with a default value.
        
        Args:
            field_name: Internal field name (e.g., "classified_as_disabled")
            field_display_name: Display name for the field (e.g., "ClassifiedAsDisabled")
            default_value: Proposed default value (e.g., "No")
            
        Returns:
            The default value if user confirms, None if user declines
        """
        console.print()
        console.print(Panel.fit(
            f"[bold yellow]Missing Mandatory Field: {field_display_name}[/bold yellow]\n\n"
            f"The field '{field_display_name}' is missing from your input file.\n"
            f"Would you like to add this field with a default value of '{default_value}'?",
            border_style="yellow",
        ))
        console.print()
        
        result = questionary.confirm(
            f"Add '{field_display_name}' with default value '{default_value}'?",
            default=True,
        ).ask()
        
        if result is None:
            raise UserAbort("User cancelled")
        
        if result:
            self.display_success(
                f"Added '{field_display_name}' with default value '{default_value}'"
            )
            return default_value
        else:
            return None
    
    def prompt_confirm_column_mappings(
        self,
        detected_mappings: dict[str, tuple[str, float]],
        all_headers: list[str],
        existing_mappings: dict[str, str],
    ) -> dict[str, str]:
        """
        Prompt user to confirm column mappings detected via variations.
        
        Args:
            detected_mappings: Dict of input_header -> (field_name, confidence)
            all_headers: All headers from input file
            existing_mappings: Already confirmed mappings (exact matches)
            
        Returns:
            Dict of confirmed mappings (input_header -> (field_name, confidence))
        """
        if not detected_mappings:
            return {}
        
        console.print()
        console.print(Panel.fit(
            "[bold yellow]Column Name Variations Detected[/bold yellow]\n\n"
            "The utility has detected that some column names in your file "
            "may be variations of the expected column names. Please confirm "
            "the mappings below.",
            border_style="yellow",
        ))
        console.print()
        
        # Show detected mappings
        mapping_table = Table(title="Detected Column Mappings", box=box.ROUNDED)
        mapping_table.add_column("Input Column", style="cyan", width=30)
        mapping_table.add_column("Maps To", style="green", width=30)
        mapping_table.add_column("Confidence", style="yellow", width=12)
        
        for input_header, (field_name, confidence) in sorted(detected_mappings.items()):
            display_name = get_field_display_name(field_name)
            confidence_pct = f"{confidence * 100:.0f}%"
            mapping_table.add_row(input_header, display_name, confidence_pct)
        
        console.print(mapping_table)
        console.print()
        
        # Show unmapped columns for reference
        mapped_headers = set(existing_mappings.keys()) | set(detected_mappings.keys())
        unmapped = [h for h in all_headers if h and h not in mapped_headers]
        
        if unmapped:
            console.print("[dim]Note: The following columns were not mapped:[/dim]")
            for header in unmapped[:10]:
                console.print(f"  [dim]- {header}[/dim]")
            if len(unmapped) > 10:
                console.print(f"  [dim]... and {len(unmapped) - 10} more[/dim]")
            console.print()
        
        # Ask for confirmation
        result = questionary.select(
            "Would you like to use these column mappings?",
            choices=[
                "Yes, use these mappings",
                "No, skip variation matching",
            ],
        ).ask()
        
        if result is None:
            raise UserAbort("User cancelled")
        
        if result == "Yes, use these mappings":
            # Convert to dict[str, str] format
            return {header: field_name for header, (field_name, _) in detected_mappings.items()}
        else:
            return {}
    
    def prompt_manual_column_mapping(
        self,
        unmatched_headers: list[str],
        existing_mappings: dict[str, str],
    ) -> dict[str, str]:
        """
        Prompt user to manually select schema fields for unmatched columns.
        
        Args:
            unmatched_headers: List of input headers that couldn't be automatically matched
            existing_mappings: Already confirmed mappings (input_header -> field_name)
            
        Returns:
            Dict of manual mappings (input_header -> field_name)
            Returns empty dict if user chooses to exit.
        """
        if not unmatched_headers:
            return {}
        
        console.print()
        console.print(Panel.fit(
            "[bold yellow]Unmatched Columns Detected[/bold yellow]\n\n"
            "Some columns in your file could not be automatically matched to the schema.\n"
            "Please manually select which schema field each column should map to, or skip it.\n"
            "You can also choose to exit if you cannot match them.",
            border_style="yellow",
        ))
        console.print()
        
        manual_mappings = {}
        mapped_field_names = set(existing_mappings.values()) | set(manual_mappings.values())
        
        # Build list of available schema fields (excluding already mapped ones)
        available_schema_fields = []
        for spec in SPORT_PASSPORT_SCHEMA:
            if spec.name not in mapped_field_names:
                display_name = get_display_name(spec)
                required_marker = " [required]" if spec.required else ""
                available_schema_fields.append({
                    "name": spec.name,
                    "display": f"{display_name}{required_marker}",
                })
        
        # Sort by required first, then alphabetically
        available_schema_fields.sort(key=lambda x: (not x["display"].endswith(" [required]"), x["display"]))
        
        # Process each unmatched header
        for header in unmatched_headers:
            console.print()
            console.print(f"[bold cyan]Column:[/bold cyan] {header}")
            console.print()
            
            # Build choices list
            choices = []
            # Add "Skip this column" option
            choices.append({
                "name": "__skip__",
                "display": "[dim]Skip this column[/dim]",
            })
            # Add available schema fields
            for field in available_schema_fields:
                choices.append({
                    "name": field["name"],
                    "display": field["display"],
                })
            # Add "Exit" option
            choices.append({
                "name": "__exit__",
                "display": "[red]Exit - cannot match this column[/red]",
            })
            
            # Prompt user to select
            selected = questionary.select(
                "Which schema field should this column map to?",
                choices=[choice["display"] for choice in choices],
            ).ask()
            
            if selected is None:
                raise UserAbort("User cancelled")
            
            # Find the selected choice
            selected_choice = None
            for choice in choices:
                if choice["display"] == selected:
                    selected_choice = choice
                    break
            
            if not selected_choice:
                raise UserAbort("Invalid selection")
            
            if selected_choice["name"] == "__exit__":
                # User chose to exit
                console.print()
                console.print("[red]Exiting - unable to match all columns.[/red]")
                raise UserAbort("User chose to exit - unable to match all columns")
            
            elif selected_choice["name"] == "__skip__":
                # User chose to skip
                console.print(f"[dim]Skipping column '{header}'[/dim]")
                continue
            
            else:
                # User selected a schema field
                field_name = selected_choice["name"]
                field_display = next(f["display"] for f in available_schema_fields if f["name"] == field_name)
                manual_mappings[header] = field_name
                mapped_field_names.add(field_name)
                
                # Remove from available fields
                available_schema_fields = [f for f in available_schema_fields if f["name"] != field_name]
                
                console.print(f"[green]✓[/green] Mapped '{header}' to '{field_display}'")
        
        if manual_mappings:
            console.print()
            console.print(f"[green]Successfully mapped {len(manual_mappings)} column(s).[/green]")
        
        return manual_mappings
    
    def confirm_export(self, output_path: str, valid_rows: int) -> bool:
        """Ask user to confirm export."""
        console.print()
        return questionary.confirm(
            f"Export {valid_rows} valid rows to {output_path}?",
            default=True,
        ).ask()
    
    def display_error(self, message: str) -> None:
        """Display an error message."""
        console.print(f"[bold red]Error:[/bold red] {message}")
    
    def display_success(self, message: str) -> None:
        """Display a success message."""
        console.print(f"[bold green]✓[/bold green] {message}")
    
    def display_info(self, message: str) -> None:
        """Display an info message."""
        console.print(f"[cyan]ℹ[/cyan] {message}")
    
    def display_warning(self, message: str) -> None:
        """Display a warning message."""
        console.print(f"[yellow]⚠[/yellow] {message}")
