# Sport Passport CSV Converter

A command-line utility to convert Excel spreadsheets into compliant CSV format for Sport Passport import.

## Features

- **Excel Input**: Read `.xlsx` or `.xls` files directly (recommended to avoid CSV parsing issues)
- **CSV Input**: Handles malformed CSV files with unquoted commas in fields and column count mismatches
- **Automatic Row Detection**: Automatically detects and removes metadata rows at the top and summary rows at the bottom of input files
- **Smart Column Mapping**: Automatically maps column headers (case-insensitive, handles asterisks in required field markers)
- **Column Name Variation Matching**: Detects common column name variations (e.g., "DOB" → "DateOfBirth", "Post Code" → "Postcode", "E-mail" → "Email") and prompts for confirmation
- **Mandatory Column Validation**: Validates that all required columns are present before processing, with helpful suggestions for similar column names
- **Auto-Correction**: Automatically fixes common issues:
  - Date format normalization (various formats → DD/MM/YYYY, including US date format conversion)
  - UK postcode formatting and spacing
  - Gender field normalization (handles abbreviations like M/F/Male/Female)
  - Yes/No field normalization (ClassifiedAsDisabled)
  - Whitespace trimming
  - Case normalization for text fields
- **Auto-Corrections Review**: Review and accept/reject all auto-corrections before they're applied
- **Corrections Log**: After applying auto-corrections, view a detailed log of all changes made to your data
- **Default Overrides**: Set default postcode and email values for all rows (common for school submissions)
- **Interactive Fixes**: Prompts for manual correction when auto-fix isn't possible
- **Validation Report**: Comprehensive summary showing:
  - Total rows processed
  - Rows skipped
  - Auto-corrections applied (with breakdown by type)
  - CSV comma repairs
  - Manual corrections

## Installation

```bash
# Navigate to the project directory
cd SportPassportCSVConverter

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Interactive Mode (Best for Non-Technical Users)

For users who prefer not to use command-line arguments, use the interactive executable:

**macOS/Linux:**
```bash
# Make sure the script is executable (first time only)
chmod +x convert_interactive.sh

# Run the interactive converter
./convert_interactive.sh
```

**Or run the Python script directly:**
```bash
# Make sure the script is executable (first time only)
chmod +x converter_interactive.py

# Activate virtual environment first
source venv/bin/activate

# Run the interactive converter
python converter_interactive.py
```

The interactive mode will:
1. Prompt you to enter the path to your input file (supports drag-and-drop from Finder/File Explorer)
2. Prompt you to specify an output file path (or use the suggested default)
3. Guide you through the conversion process step-by-step

This is perfect if you're not comfortable with command-line arguments!

### Quick Start (Command-Line Mode)

Use the provided shell script which handles environment activation automatically:

```bash
# Make sure the script is executable (first time only)
chmod +x convert.sh

# Basic usage
./convert.sh input.xlsx

# With output file
./convert.sh input.xlsx -o output.csv

# With default postcode and email
./convert.sh input.xlsx --postcode "SW1A 1AA" --email "school@example.com"

# Non-interactive mode (skip all prompts)
./convert.sh input.xlsx --postcode "SW1A 1AA" --email "school@example.com" -y

# Show help
./convert.sh
```

### Manual Usage

If you prefer to manage the virtual environment yourself:

```bash
# Step 1: Activate the virtual environment
source venv/bin/activate

# Step 2: Run the converter
python -m converter input.xlsx

# Step 3: Deactivate when done (optional)
deactivate
```

### Command Line Options

```
python -m converter <input_file> [options]

Arguments:
  input_file              Excel (.xlsx/.xls) or CSV file to convert

Options:
  -o, --output FILE       Output CSV file path (default: input.converted.csv)
  -y, --yes               Auto-confirm export without prompting
  --postcode POSTCODE     Default postcode to apply to ALL rows
  --email EMAIL           Default email to apply to ALL rows
```

### Examples

```bash
# Basic conversion (interactive mode)
./convert.sh data.xlsx

# Specify output file
./convert.sh data.xlsx -o cleaned_data.csv

# Convert CSV file (repairs malformed rows with comma issues and column mismatches)
./convert.sh data.csv -o output.csv

# Set default postcode and email for all rows
./convert.sh data.xlsx --postcode "SW1A 1AA" --email "admin@school.edu"

# Fully automated (no prompts)
./convert.sh data.xlsx -o output.csv --postcode "SW1A 1AA" --email "admin@school.edu" -y
```

## Default Postcode and Email Override

Schools typically submit forms where all members share the same postcode (the school's address) and contact email. The converter supports setting these default values in two ways:

### Interactive Mode (default)

When you run the converter, you'll be prompted:

```
Would you like to set default values for Postcode and Email? (y/N)
```

If you choose yes, you can enter:
- A default UK postcode (e.g., `SW1A 1AA`) - applied to ALL rows
- A default email address (e.g., `admin@school.edu`) - applied to ALL rows

### Command Line Mode

For scripted/batch processing, use the `--postcode` and `--email` arguments:

```bash
python -m converter input.xlsx --postcode "SW1A 1AA" --email "admin@school.edu" -y
```

Both values are validated before being applied and will overwrite any existing values in those columns.

### Automatic Column Addition

If you provide default postcode or email values (via command line or interactive prompt) but the corresponding columns are missing from your input file, the converter will automatically add these columns and populate them with the default values. This ensures the conversion succeeds even when columns are missing, as long as defaults are provided.

## Automatic Row Detection

The converter automatically detects and removes:
- **Metadata rows at the top**: Headers, titles, generation dates, etc. that appear before the actual column headers
- **Summary rows at the bottom**: Totals, footers, "End of report" messages, etc.

When rows are detected for removal, you'll be shown a preview and asked to confirm. In auto-confirm mode (`-y` flag), rows are automatically removed without prompting.

## Column Name Variations

The converter recognizes common variations of column names and will prompt you to confirm the mapping. Examples:

- **Date of Birth**: `DOB`, `Date of Birth`, `Birth Date`, `DateOfBirth`
- **Postcode**: `Post Code`, `Postal Code`, `ZIP Code`, `Postcode`, `School Postcode`, `School Post Code`
- **Email**: `E-mail`, `E-Mail`, `Email Address`, `Mail`
- **First Name**: `Given Name`, `Forename`, `First`, `FName`
- **Surname**: `Last Name`, `Family Name`, `Second Name`, `LName`

When variations are detected, you'll see a table showing the detected mappings with confidence scores, and can choose to accept or reject them.

### Manual Column Matching

If a column in your input file cannot be automatically matched (even after variation detection), you'll be presented with a manual selection menu. For each unmatched column, you can:

1. **Select a schema field**: Choose which schema field the column should map to from a list of available fields
2. **Skip the column**: Choose to skip the column if it's not needed
3. **Exit**: If you cannot determine the correct mapping, you can exit the conversion

This ensures that even unusual or non-standard column names can be properly mapped to the schema. The menu shows required fields with a `[required]` marker to help you prioritize important mappings.

## Required Fields

The following fields are mandatory (marked with * in template):

- First Name
- Surname
- Gender (Male/Female/Other)
- ClassifiedAsDisabled (Yes/No)
- DateOfBirth (DD/MM/YYYY)
- Postcode (UK format)
- Email

### Handling Missing Mandatory Fields

If a mandatory field is missing from your input file, the converter will prompt you to add it with a default value:

- **ClassifiedAsDisabled**: Defaults to "No" if missing
- **Postcode**: Uses the default postcode if provided via `--postcode` or interactive prompt
- **Email**: Uses the default email if provided via `--email` or interactive prompt
- **Other mandatory fields**: You'll be prompted to provide a value (no automatic default)

If you decline to add a missing mandatory field, the conversion will exit. In auto-confirm mode (`-y` flag), missing fields with defaults are automatically added.

## Processing Workflow

1. **Load Input**: Reads Excel or CSV files
2. **Detect Superfluous Rows**: Automatically identifies and removes metadata rows at the top and summary rows at the bottom (with user confirmation)
3. **Map Column Headers**: Maps input columns to schema columns, including:
   - Exact matches (case-insensitive, with/without asterisks)
   - Common variations (e.g., "DOB" → "DateOfBirth", "Post Code" → "Postcode")
   - User confirmation for variation matches
   - Manual selection menu for unmatched columns (if automatic matching fails)
4. **Validate Mandatory Columns**: Ensures all required columns are present before proceeding
5. **Normalize Data**: Applies standard normalizations (trimming, case handling, etc.)
6. **Validate & Collect Errors**: Identifies validation errors and categorizes them as auto-fixable or manual
7. **Review Auto-Corrections**: Displays all proposed auto-corrections for user review (can accept all or review manually)
8. **Apply Auto-Corrections**: Applies accepted auto-corrections to the data
9. **View Corrections Log** (optional): After applying corrections, you can view a detailed log of all changes made
10. **Interactive Fixes**: Prompts for manual correction of errors that can't be auto-fixed
11. **Apply Default Overrides**: Applies default postcode/email values if set
12. **Display Summary**: Shows comprehensive report of all processing
13. **Review Changes Before Export** (optional): Before generating the final output, you can review all changes (auto-corrections and manual corrections) that were made to your data
14. **Export**: Generates compliant CSV file

## Output

The generated CSV file will:
- Match the exact Sport Passport column order (20 columns)
- Quote all text fields to prevent comma-related issues
- Apply any default postcode/email overrides to all rows
- Be fully compliant for Sport Passport import

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_interactive.py -v
```

## Packaging and Distribution

This utility can be packaged for distribution in multiple ways. See [PACKAGING.md](PACKAGING.md) for detailed instructions.

### Quick Start: Build for Distribution

**Option 1: Python Package (pip installable)**
```bash
chmod +x build-package.sh
./build-package.sh
# Creates .whl file in dist/ directory
```

**Option 2: Standalone Executable (interactive version, no Python required)**
```bash
chmod +x build-executable.sh
./build-executable.sh
# Creates interactive executable in dist/ directory
```

After building, distribute the files from the `dist/` directory to your users.

### Installation from Package

Users with Python can install from the wheel file:
```bash
pip install dist/sport-passport-csv-converter-*.whl
```

After installation, users can run:
```bash
sport-passport-converter input.xlsx
# or
sp-converter input.xlsx
```

For more details on packaging, distribution options, and platform-specific instructions, see [PACKAGING.md](PACKAGING.md).
