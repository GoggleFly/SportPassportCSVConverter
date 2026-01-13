#!/bin/bash
#
# Sport Passport CSV Converter - Quick Run Script
# 
# Usage:
#   ./convert.sh input.xlsx
#   ./convert.sh input.xlsx -o output.csv
#   ./convert.sh input.xlsx --postcode "SW1A 1AA" --email "school@example.com"
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Error: Virtual environment not found."
    echo "Please run the following commands first:"
    echo ""
    echo "  cd $SCRIPT_DIR"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo ""
    exit 1
fi

# Check if at least one argument provided
if [ $# -eq 0 ]; then
    echo "Sport Passport CSV Converter"
    echo ""
    echo "Usage: ./convert.sh <input_file> [options]"
    echo ""
    echo "Arguments:"
    echo "  input_file              Excel (.xlsx/.xls) or CSV file to convert"
    echo ""
    echo "Options:"
    echo "  -o, --output FILE       Output CSV file path"
    echo "  -y, --yes               Auto-confirm without prompts"
    echo "  --postcode POSTCODE     Default postcode for all rows"
    echo "  --email EMAIL           Default email for all rows"
    echo ""
    echo "Examples:"
    echo "  ./convert.sh data.xlsx"
    echo "  ./convert.sh data.xlsx -o converted.csv"
    echo "  ./convert.sh data.xlsx --postcode \"SW1A 1AA\" --email \"school@example.com\" -y"
    echo ""
    exit 0
fi

# Activate virtual environment and run converter
source "$SCRIPT_DIR/venv/bin/activate"
python -m converter "$@"
EXIT_CODE=$?
deactivate

exit $EXIT_CODE
