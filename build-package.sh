#!/bin/bash
#
# Build script for Sport Passport CSV Converter
# Creates both source distribution and wheel package
#

set -e

echo "Building Sport Passport CSV Converter..."
echo ""

# Ensure we have required tools
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed"
    exit 1
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/
rm -rf dist/
rm -rf *.egg-info/
rm -rf src/*.egg-info/

# Install build dependencies
echo "Installing build dependencies..."
python3 -m pip install --upgrade pip build wheel setuptools

# Build source distribution and wheel
echo ""
echo "Building package..."
python3 -m build

echo ""
echo "✓ Build complete!"
echo ""
echo "Built packages are in the dist/ directory:"
ls -lh dist/
echo ""
echo "To install the package:"
echo "  pip install dist/sport-passport-csv-converter-*.whl"
echo ""
echo "Or upload to PyPI:"
echo "  python3 -m twine upload dist/*"
