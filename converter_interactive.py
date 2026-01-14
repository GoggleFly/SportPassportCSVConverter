#!/usr/bin/env python3
"""
Interactive Sport Passport CSV Converter
Prompts user for input and output file paths.
"""

import sys
import shlex
import re
from pathlib import Path

# Add the project root directory to the path so we can import converter module
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from converter.main import SportPassportConverter
from converter.interactive import InteractiveCorrector


def parse_file_path(path_input: str) -> str:
    """
    Parse and clean a file path from user input.
    
    Handles:
    - Quoted paths (single or double quotes)
    - Paths with spaces (quoted, unquoted, or backslash-escaped)
    - Trailing whitespace after file extensions
    - macOS drag-and-drop paths with backslash-escaped spaces
    
    Args:
        path_input: Raw input string from user
        
    Returns:
        Cleaned file path string
    """
    if not path_input:
        return ""
    
    # First, strip leading/trailing whitespace
    path_input = path_input.strip()
    
    if not path_input:
        return ""
    
    # Always try to use shlex.split() first - it handles:
    # - Quoted paths (single or double quotes)
    # - Backslash-escaped spaces (macOS drag-and-drop)
    # - Other shell escaping
    try:
        parsed = shlex.split(path_input, posix=True)
        
        if len(parsed) == 1:
            # Single result - shlex successfully parsed it (handled quotes/escapes)
            path = parsed[0]
        elif len(parsed) > 1:
            # Multiple results - means there were unquoted, unescaped spaces
            # In this case, treat the entire original input as a single path
            # (user likely pasted a path with spaces without quotes/escapes)
            path = path_input
        else:
            # Empty result - might be empty quoted string
            # Check if it was quoted and extract content
            if (path_input.startswith('"') and path_input.endswith('"')) or \
               (path_input.startswith("'") and path_input.endswith("'")):
                path = path_input[1:-1].strip()
            else:
                path = path_input
    except ValueError:
        # shlex parsing failed (malformed quotes, etc.)
        # Fall back to manual quote removal
        if (path_input.startswith('"') and path_input.endswith('"')) or \
           (path_input.startswith("'") and path_input.endswith("'")):
            path = path_input[1:-1].strip()
        else:
            # Not quoted, use as-is (might have backslash escapes that shlex couldn't handle)
            # Try to manually handle backslash-escaped spaces
            path = path_input.replace('\\ ', ' ')
    
    # Trim trailing whitespace after file extension
    # Match pattern: filename.extension followed by whitespace
    # This regex finds a file extension pattern and any trailing whitespace after it
    extension_pattern = r'(\.[a-zA-Z0-9]+)\s+$'
    path = re.sub(extension_pattern, r'\1', path)
    
    # Also handle case where there's whitespace before the extension
    # e.g., "file .csv " -> "file.csv"
    path = re.sub(r'\s+\.([a-zA-Z0-9]+)\s*$', r'.\1', path)
    
    return path


def get_input_file() -> Path:
    """Prompt user for input file path with validation."""
    interactive = InteractiveCorrector()
    
    while True:
        print("\n" + "="*60)
        print("Sport Passport CSV Converter - Interactive Mode")
        print("="*60)
        print("\nPlease provide the path to your input file.")
        print("Supported formats: .xlsx, .xls, .csv")
        print()
        
        input_path_raw = input("Input file path: ")
        input_path = parse_file_path(input_path_raw)
        
        if not input_path:
            print("❌ Please enter a file path.")
            continue
        
        # Expand user home directory and resolve relative paths
        input_file = Path(input_path).expanduser().resolve()
        
        if not input_file.exists():
            print(f"❌ Error: File not found: {input_file}")
            print("Please check the path and try again.")
            retry = input("\nTry again? (y/N): ").strip().lower()
            if retry != 'y':
                sys.exit(1)
            continue
        
        if not input_file.is_file():
            print(f"❌ Error: Path is not a file: {input_file}")
            retry = input("\nTry again? (y/N): ").strip().lower()
            if retry != 'y':
                sys.exit(1)
            continue
        
        # Check file extension
        suffix = input_file.suffix.lower()
        if suffix not in ('.xlsx', '.xls', '.csv'):
            print(f"❌ Error: Unsupported file format: {suffix}")
            print("Please provide a .xlsx, .xls, or .csv file.")
            retry = input("\nTry again? (y/N): ").strip().lower()
            if retry != 'y':
                sys.exit(1)
            continue
        
        print(f"✓ Found: {input_file}")
        return input_file


def get_output_file(input_file: Path) -> Path:
    """Prompt user for output file path with validation."""
    # Suggest default output name
    default_output = input_file.with_suffix('.converted.csv')
    
    print("\n" + "-"*60)
    print("Where would you like to save the converted file?")
    print(f"\nDefault (press Enter to use): {default_output}")
    print()
    
    output_path_raw = input("Output file path (or press Enter for default): ")
    output_path = parse_file_path(output_path_raw)
    
    # Use default if empty
    if not output_path:
        output_file = default_output
    else:
        output_file = Path(output_path).expanduser().resolve()
    
    # Ensure .csv extension (normalize to lowercase)
    if output_file.suffix.lower() == '.csv':
        # Already a CSV file, but may be uppercase - normalize to lowercase
        if output_file.suffix != '.csv':
            output_file = output_file.with_suffix('.csv')
    else:
        # Not a CSV file, add/replace extension
        output_file = output_file.with_suffix('.csv')
    
    # Check if output directory exists
    output_dir = output_file.parent
    if not output_dir.exists():
        print(f"\nDirectory doesn't exist: {output_dir}")
        create = input("Would you like to create it? (y/N): ").strip().lower()
        if create == 'y':
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                print(f"✓ Created directory: {output_dir}")
            except Exception as e:
                print(f"❌ Error creating directory: {e}")
                sys.exit(1)
        else:
            print("Please specify a different output path.")
            return get_output_file(input_file)
    
    # Check if output file already exists
    if output_file.exists():
        print(f"\n⚠️  Warning: File already exists: {output_file}")
        overwrite = input("Overwrite? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("Please specify a different output path.")
            return get_output_file(input_file)
    
    print(f"✓ Output will be saved to: {output_file}\n")
    return output_file


def main():
    """Main entry point for interactive converter."""
    try:
        # Get input file
        input_file = get_input_file()
        
        # Get output file
        output_file = get_output_file(input_file)
        
        # Create and run converter
        print("="*60)
        print("Starting conversion...")
        print("="*60 + "\n")
        
        converter = SportPassportConverter(
            str(input_file),
            str(output_file),
            auto_confirm=False,  # Always interactive
        )
        
        success = converter.run()
        
        if success:
            print("\n" + "="*60)
            print("✓ Conversion completed successfully!")
            print("="*60)
            sys.exit(0)
        else:
            print("\n" + "="*60)
            print("⚠️  Conversion completed with issues or was cancelled.")
            print("="*60)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nConversion cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()