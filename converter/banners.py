"""ASCII art banners and visual separators for the conversion process."""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

# ASCII Art Constants - Simple and clear designs

DISCLAIMER_TEXT = (
    "⚠️  DISCLAIMER: This utility is NOT affiliated with, provided by, or "
    "supported by Sport Passport.\n"
    "It is a convenience utility only to ease the sometimes painful process "
    "of data cleanup and alignment to the required format to allow for an easier life!"
)


def display_welcome_banner() -> None:
    """Display welcome banner with clear title and disclaimer."""
    console.print()
    
    # Simple welcome banner with clear title - using Panel for clean rendering
    console.print(Panel.fit(
        "[bold cyan]Sport Passport CSV Converter[/bold cyan]\n"
        "[dim]A helpful tool for data conversion[/dim]",
        border_style="cyan",
        box=box.ROUNDED,
        title="[cyan]Welcome[/cyan]",
    ))
    console.print()
    
    # Display disclaimer in a warning panel
    console.print(Panel(
        f"[bold yellow]{DISCLAIMER_TEXT}[/bold yellow]",
        border_style="yellow",
        box=box.ROUNDED,
        title="[yellow]⚠️  Important Notice[/yellow]",
    ))
    console.print()


def display_step_separator(step_name: str, step_number: int = None) -> None:
    """
    Display a visual separator banner for a processing step.
    
    Args:
        step_name: Name of the step (e.g., "LOADING INPUT FILE")
        step_number: Optional step number to display
    """
    console.print()
    console.print()
    
    # Build the step label
    if step_number is not None:
        step_label = f"STEP {step_number}: {step_name}"
    else:
        step_label = step_name
    
    # Create bordered text
    step_text = Text(step_label, style="bold cyan", justify="center")
    
    # Create a panel with the step name
    console.print(
        Panel.fit(
            step_text,
            border_style="cyan",
            box=box.ROUNDED,
        )
    )
    console.print()


def display_completion_banner(success: bool = True) -> None:
    """
    Display completion banner with clear success/failure message.
    
    Args:
        success: True for success, False for failure/cancellation
    """
    console.print()
    console.print()
    
    if success:
        symbol = "✓"
        message = "[bold green]Conversion Completed Successfully![/bold green]"
        border_style = "green"
        title = "[green]✓ Success[/green]"
    else:
        symbol = "✗"
        message = "[bold red]Conversion Failed or Cancelled[/bold red]"
        border_style = "red"
        title = "[red]✗ Failed[/red]"
    
    # Simple, clear completion banner
    completion_content = Text()
    completion_content.append(f"  {symbol}  ", style=f"bold {border_style}")
    completion_content.append(message, style=f"bold {border_style}")
    
    console.print(Panel.fit(
        completion_content,
        border_style=border_style,
        box=box.ROUNDED,
        title=title,
    ))
    console.print()
