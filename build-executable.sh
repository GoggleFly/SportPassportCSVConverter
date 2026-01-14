#!/bin/bash
#
# Build standalone executable using PyInstaller
# Creates a single-file executable (interactive version) that doesn't require Python installation
#

set -e

echo "Building standalone executable for Sport Passport CSV Converter..."
echo ""

# Ensure we have required tools
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed"
    exit 1
fi

# Install PyInstaller if not already installed
if ! python3 -m pip show pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    python3 -m pip install pyinstaller
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/
rm -rf dist/
rm -rf *.spec.bak

# Build executable (interactive version only)
echo "Building standalone executable (interactive mode)..."
python3 -m PyInstaller sport-passport-converter.spec --clean --noconfirm

echo ""
echo "✓ Build complete!"
echo ""
echo "Executable is in the dist/ directory:"
ls -lh dist/

# Detect OS and provide appropriate instructions
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "macOS executable created: dist/sport-passport-converter"
    echo ""
    echo "To distribute:"
    echo "  1. Test the executable: ./dist/sport-passport-converter"
    echo "  2. Create a .zip file with the executable"
    echo "  3. Optional: Create a .dmg installer for easier distribution"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    echo "Linux executable created: dist/sport-passport-converter"
    echo ""
    echo "To distribute:"
    echo "  1. Test the executable: ./dist/sport-passport-converter"
    echo "  2. Create a .tar.gz archive with the executable"
    echo "  3. Note: May need to build on target OS/architecture"
else
    echo ""
    echo "Executable created: dist/sport-passport-converter"
fi
