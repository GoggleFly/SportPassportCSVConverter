#!/bin/bash
#
# Sport Passport CSV Converter - Interactive Launcher
# 
# Double-click this file or run: ./convert_interactive.sh
# 
# This script will prompt you for your input and output file paths.

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
    read -p "Press Enter to exit..."
    exit 1
fi

# Activate virtual environment and run interactive converter
source "$SCRIPT_DIR/venv/bin/activate"
python "$SCRIPT_DIR/converter_interactive.py"
EXIT_CODE=$?
deactivate

# On macOS/Linux, keep terminal open if launched via double-click
if [ -z "$TERM" ] || [ "$TERM" = "dumb" ]; then
    echo ""
    read -p "Press Enter to exit..."
fi

exit $EXIT_CODE